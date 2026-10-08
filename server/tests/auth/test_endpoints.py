from collections.abc import AsyncIterator
from unittest.mock import MagicMock

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient
from pytest_mock import MockerFixture
from reauth.amr import AuthenticationMethodReference

from outception.auth.authentication_session import TOKEN_PREFIX
from outception.auth.factors import EMAIL_OTP_ADDRESS_CEILING, EMAIL_OTP_HOURLY_CAP
from outception.auth.models import AuthSubject
from outception.config import settings
from outception.kit.crypto import generate_token_hash_pair
from outception.kit.utils import utc_now
from outception.models import AuthenticationSession, User
from outception.postgres import AsyncSession
from tests.fixtures.auth import make_session_stale
from tests.fixtures.base import IsolatedSessionTestClient
from tests.fixtures.database import SaveFixture


@pytest_asyncio.fixture
async def cookie_client(
    app: FastAPI, session: AsyncSession
) -> AsyncIterator[httpx.AsyncClient]:
    # https://test matches the Secure session cookies' domain
    async with IsolatedSessionTestClient(
        session=session,
        auto_expunge=False,
        transport=httpx.ASGITransport(app=app),
        base_url="https://test",
    ) as client:
        yield client


async def create_completable_authentication_session(
    save_fixture: SaveFixture, user: User
) -> str:
    token, token_hash = generate_token_hash_pair(prefix=TOKEN_PREFIX)
    authentication_session = AuthenticationSession(
        token_hash=token_hash,
        expires_at=int(utc_now().timestamp()) + 900,
        step=1,
        authentication_method_references=[AuthenticationMethodReference.EMAIL],
        used_factors=["email_otp"],
        context=None,
        identity_id=user.id,
    )
    await save_fixture(authentication_session)
    return token


@pytest.mark.asyncio
class TestComplete:
    async def test_anonymous(self, cookie_client: httpx.AsyncClient) -> None:
        response = await cookie_client.get("/v1/auth/complete")

        assert response.status_code == 401
        assert response.json()["error"] == "InvalidAuthenticationSession"

    async def test_non_ascii_cookie(self, cookie_client: httpx.AsyncClient) -> None:
        non_ascii_cookie = (
            settings.AUTHENTICATION_SESSION_COOKIE_KEY.encode()
            + b"=token-\xe4\xb8\xad\xe6\x96\x87"
        )
        response = await cookie_client.get(
            "/v1/auth/complete", headers=[(b"cookie", non_ascii_cookie)]
        )

        assert response.status_code == 401
        assert response.json()["error"] == "InvalidAuthenticationSession"

    async def test_valid(
        self,
        cookie_client: httpx.AsyncClient,
        save_fixture: SaveFixture,
        user: User,
    ) -> None:
        token = await create_completable_authentication_session(save_fixture, user)
        cookie_client.cookies.set(settings.AUTHENTICATION_SESSION_COOKIE_KEY, token)

        response = await cookie_client.get("/v1/auth/complete")

        assert response.status_code == 303
        assert settings.USER_SESSION_COOKIE_KEY in response.cookies

    @pytest.mark.auth
    async def test_replay_with_user_session(
        self,
        cookie_client: httpx.AsyncClient,
        save_fixture: SaveFixture,
        user: User,
    ) -> None:
        token = await create_completable_authentication_session(save_fixture, user)
        cookie_client.cookies.set(settings.AUTHENTICATION_SESSION_COOKIE_KEY, token)

        first = await cookie_client.get("/v1/auth/complete")
        assert first.status_code == 303

        cookie_client.cookies.clear()
        replay = await cookie_client.get("/v1/auth/complete")

        assert replay.status_code == 303
        assert replay.headers["location"] == settings.generate_frontend_url(
            settings.FRONTEND_DEFAULT_RETURN_PATH
        )


@pytest.mark.asyncio
class TestTOTPEnroll:
    async def test_anonymous(self, client: AsyncClient) -> None:
        response = await client.post("/v1/auth/totp")

        assert response.status_code == 401

    @pytest.mark.auth
    async def test_stale_session(
        self, client: AsyncClient, auth_subject: AuthSubject[User]
    ) -> None:
        make_session_stale(auth_subject)

        response = await client.post("/v1/auth/totp")

        assert response.status_code == 403
        assert response.json()["error"] == "SessionNotFreshError"

    @pytest.mark.auth
    async def test_fresh_session(self, client: AsyncClient) -> None:
        response = await client.post("/v1/auth/totp")

        assert response.status_code == 201
        json = response.json()
        assert json["secret"]
        assert json["provisioning_uri"]


@pytest.mark.asyncio
class TestTOTPEnable:
    @pytest.mark.auth
    async def test_stale_session(
        self, client: AsyncClient, auth_subject: AuthSubject[User]
    ) -> None:
        make_session_stale(auth_subject)

        response = await client.post("/v1/auth/totp/enable", json={"code": "123456"})

        assert response.status_code == 403
        assert response.json()["error"] == "SessionNotFreshError"

    @pytest.mark.auth
    async def test_fresh_session_not_enrolled(self, client: AsyncClient) -> None:
        response = await client.post("/v1/auth/totp/enable", json={"code": "123456"})

        assert response.status_code == 403
        assert response.json()["error"] != "SessionNotFreshError"


@pytest.mark.asyncio
class TestTOTPDelete:
    @pytest.mark.auth
    async def test_stale_session(
        self, client: AsyncClient, auth_subject: AuthSubject[User]
    ) -> None:
        make_session_stale(auth_subject)

        response = await client.delete("/v1/auth/totp")

        assert response.status_code == 403
        assert response.json()["error"] == "SessionNotFreshError"

    @pytest.mark.auth
    async def test_fresh_session_not_enrolled(self, client: AsyncClient) -> None:
        response = await client.delete("/v1/auth/totp")

        assert response.status_code == 404


@pytest.mark.asyncio
class TestBackupCodesEnroll:
    @pytest.mark.auth
    async def test_stale_session(
        self, client: AsyncClient, auth_subject: AuthSubject[User]
    ) -> None:
        make_session_stale(auth_subject)

        response = await client.post("/v1/auth/backup-codes")

        assert response.status_code == 403
        assert response.json()["error"] == "SessionNotFreshError"

    @pytest.mark.auth
    async def test_fresh_session(self, client: AsyncClient) -> None:
        response = await client.post("/v1/auth/backup-codes")

        assert response.status_code == 201
        assert len(response.json()["codes"]) > 0


async def request_email_otp(
    client: httpx.AsyncClient,
    mocker: MockerFixture,
    email: str,
) -> tuple[httpx.Response, MagicMock]:
    mocker.patch("outception.auth.endpoints.verify_turnstile")
    enqueue_email_template = mocker.patch(
        "outception.auth.factors.enqueue_email_template"
    )

    start = await client.post(
        "/v1/auth/start",
        json={"return_to": "/dashboard"},
    )
    assert start.status_code == 201

    response = await client.post(
        "/v1/auth/email-otp/request",
        json={"email": email, "cf-turnstile-response": "turnstile-token"},
    )
    return response, enqueue_email_template


@pytest.mark.asyncio
class TestEmailOTPRequest:
    async def test_one_address_is_capped_across_sessions(
        self, login_client: httpx.AsyncClient, mocker: MockerFixture
    ) -> None:
        # Every request starts a fresh authentication session: the per-session
        # allowance never trips, the per-address one does.
        for _ in range(EMAIL_OTP_HOURLY_CAP):
            response, _ = await request_email_otp(
                login_client, mocker, "target@acme.com"
            )
            assert response.status_code == 202
        response, enqueue_email_template = await request_email_otp(
            login_client, mocker, "Target@acme.com"
        )
        assert response.status_code == 429
        enqueue_email_template.assert_not_called()

    async def test_someone_else_cannot_use_up_the_owners_codes(
        self, login_client: httpx.AsyncClient, mocker: MockerFixture
    ) -> None:
        ip = mocker.patch("outception.auth.endpoints.get_ip_address")
        ip.return_value = "198.51.100.7"
        for _ in range(EMAIL_OTP_HOURLY_CAP):
            response, _ = await request_email_otp(
                login_client, mocker, "target@acme.com"
            )
            assert response.status_code == 202
        response, _ = await request_email_otp(login_client, mocker, "target@acme.com")
        assert response.status_code == 429
        # The owner, on their own network, still gets a code.
        ip.return_value = "203.0.113.9"
        response, sent = await request_email_otp(
            login_client, mocker, "target@acme.com"
        )
        assert response.status_code == 202
        sent.assert_called_once()

    async def test_many_networks_still_meet_a_ceiling(
        self, login_client: httpx.AsyncClient, mocker: MockerFixture
    ) -> None:
        ip = mocker.patch("outception.auth.endpoints.get_ip_address")
        for n in range(EMAIL_OTP_ADDRESS_CEILING):
            ip.return_value = f"192.0.2.{n + 1}"
            response, _ = await request_email_otp(
                login_client, mocker, "target@acme.com"
            )
            assert response.status_code == 202
        ip.return_value = "192.0.2.250"
        response, sent = await request_email_otp(
            login_client, mocker, "target@acme.com"
        )
        assert response.status_code == 429
        sent.assert_not_called()

    async def test_request(
        self, login_client: httpx.AsyncClient, mocker: MockerFixture
    ) -> None:
        response, enqueue_email_template = await request_email_otp(
            login_client, mocker, "jane@acme.com"
        )

        assert response.status_code == 202
        enqueue_email_template.assert_called_once()


@pytest.mark.asyncio
class TestLogout:
    async def test_cross_site_navigation_is_refused(
        self, client: httpx.AsyncClient
    ) -> None:
        response = await client.get(
            "/v1/auth/logout",
            headers={"sec-fetch-site": "cross-site"},
            follow_redirects=False,
        )
        assert response.status_code == 403

    async def test_same_site_navigation_logs_out(
        self, client: httpx.AsyncClient
    ) -> None:
        response = await client.get(
            "/v1/auth/logout",
            headers={"sec-fetch-site": "same-site"},
            follow_redirects=False,
        )
        assert response.status_code in (302, 303, 307)


@pytest.mark.asyncio
@pytest.mark.parametrize("error", ["access_denied", "user_cancelled_authorize"])
async def test_a_refused_provider_sign_in_comes_back_as_its_code(
    client: AsyncClient, error: str
) -> None:
    """The provider's own wording (an AADSTS description, say) never
    reaches the page; the code does, and the page says it in its words."""
    client.cookies.set(settings.OAUTH2_SESSION_STATE_COOKIE_KEY, "state")
    response = await client.get(
        "/v1/auth/google/callback",
        params={
            "state": "state",
            "error": error,
            "error_description": "AADSTS65004: User declined to consent",
        },
    )
    location = response.headers["location"]
    assert "error=access_denied" in location
    assert "AADSTS" not in location
