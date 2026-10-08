from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import jwt
import pytest
import pytest_asyncio
from httpx import AsyncClient
from pytest_mock import MockerFixture
from sqlalchemy import select

from outception.auth.scope import Scope
from outception.auth.service import USER_SESSION_TOKEN_PREFIX
from outception.config import settings
from outception.kit.crypto import generate_token_hash_pair, get_token_hash
from outception.kit.db.postgres import Session
from outception.kit.encryption import EncryptedString
from outception.kit.hash_secrets import HashSecrets
from outception.kit.utils import utc_now
from outception.models import (
    OAuth2Client,
    OAuth2Grant,
    OAuth2Token,
    User,
    UserSession,
)
from outception.oauth2.service.oauth2_grant import oauth2_grant as oauth2_grant_service
from outception.oauth2.sub_type import SubType
from tests.fixtures.auth import AuthSubjectFixture
from tests.fixtures.database import SaveFixture

from ..conftest import create_oauth2_authorization_code, create_oauth2_token


@pytest_asyncio.fixture
async def oauth2_client(save_fixture: SaveFixture, user: User) -> OAuth2Client:
    oauth2_client = OAuth2Client(client_id="outception_ci_123", user=user)
    await oauth2_client.set_client_secret("outception_cs_123")
    await oauth2_client.set_registration_access_token("outception_crt_123")
    oauth2_client.set_client_metadata(
        {
            "client_name": "Test Client",
            "redirect_uris": ["http://127.0.0.1:8000/docs/oauth2-redirect"],
            "token_endpoint_auth_method": "client_secret_post",
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "scope": "openid profile email",
            "default_sub_type": "user",
        }
    )
    await save_fixture(oauth2_client)
    return oauth2_client


@pytest_asyncio.fixture
async def public_oauth2_client(save_fixture: SaveFixture, user: User) -> OAuth2Client:
    oauth2_client = OAuth2Client(client_id="outception_ci_123", user=user)
    await oauth2_client.set_client_secret("outception_cs_123")
    await oauth2_client.set_registration_access_token("outception_crt_123")
    oauth2_client.set_client_metadata(
        {
            "client_name": "Test Client",
            "redirect_uris": ["http://127.0.0.1:8000/docs/oauth2-redirect"],
            "token_endpoint_auth_method": "none",
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "scope": "openid profile email",
            "default_sub_type": "user",
        }
    )
    await save_fixture(oauth2_client)
    return oauth2_client


@pytest_asyncio.fixture
async def first_party_oauth2_client(
    save_fixture: SaveFixture, user: User
) -> OAuth2Client:
    oauth2_client = OAuth2Client(
        client_id="outception_ci_123", first_party=True, user=user
    )
    await oauth2_client.set_client_secret("outception_cs_123")
    await oauth2_client.set_registration_access_token("outception_crt_123")
    oauth2_client.set_client_metadata(
        {
            "client_name": "Test Client",
            "redirect_uris": ["http://127.0.0.1:8000/docs/oauth2-redirect"],
            "token_endpoint_auth_method": "client_secret_post",
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "scope": "openid profile email",
            "default_sub_type": "user",
        }
    )
    await save_fixture(oauth2_client)
    return oauth2_client


@pytest_asyncio.fixture
async def web_grant_oauth2_client(
    save_fixture: SaveFixture, user: User
) -> OAuth2Client:
    oauth2_client = OAuth2Client(client_id="outception_ci_123", user=user)
    await oauth2_client.set_client_secret("outception_cs_123")
    await oauth2_client.set_registration_access_token("outception_crt_123")
    oauth2_client.set_client_metadata(
        {
            "client_name": "Test Client",
            "redirect_uris": ["http://127.0.0.1:8000/docs/oauth2-redirect"],
            "token_endpoint_auth_method": "client_secret_post",
            "grant_types": ["web"],
            "response_types": [],
            "scope": "openid profile email",
        }
    )
    await save_fixture(oauth2_client)
    return oauth2_client


async def create_oauth2_grant(
    save_fixture: SaveFixture,
    *,
    client: OAuth2Client,
    scopes: list[str],
    user: User | None = None,
) -> OAuth2Grant:
    oauth2_grant = OAuth2Grant(
        client_id=client.client_id,
        user_id=user.id if user is not None else None,
        scope=" ".join(scopes),
    )
    await save_fixture(oauth2_grant)
    return oauth2_grant


@pytest.mark.asyncio
class TestOAuth2Register:
    @pytest.mark.parametrize(
        "redirect_uri",
        [
            "http://example.com",
            "foobar",
            f"http://{'a' * 54773}slocalhost/callback",
            "http://localhost.evil/callback",
            "http://localhostevil/callback",
            "http://localhost./callback",
        ],
    )
    @pytest.mark.auth
    async def test_invalid_redirect_uri(
        self, redirect_uri: str, client: AsyncClient
    ) -> None:
        response = await client.post(
            "/v1/oauth2/register",
            json={"client_name": "Test Client", "redirect_uris": [redirect_uri]},
        )

        assert response.status_code == 422

    @pytest.mark.auth(
        AuthSubjectFixture(subject="anonymous"),
        AuthSubjectFixture(subject="user"),
    )
    @pytest.mark.parametrize(
        "redirect_uri",
        [
            "https://example.com",
            "http://localhost:8000/callback",
            "http://foo.localhost:8000/callback",
            "http://127.0.0.1:8000/callback",
        ],
    )
    async def test_valid(self, redirect_uri: str, client: AsyncClient) -> None:
        response = await client.post(
            "/v1/oauth2/register",
            json={
                "client_name": "Test Client",
                "redirect_uris": [redirect_uri],
                "scope": "openid email",
            },
        )

        assert response.status_code == 201
        json = response.json()

        assert "registration_access_token" in json
        assert json["token_endpoint_auth_method"] == "client_secret_post"
        assert json["scope"] == "openid email"
        for value in json.values():
            assert value is not None

    @pytest.mark.auth(AuthSubjectFixture(subject="user"))
    async def test_valid_public_client(self, client: AsyncClient) -> None:
        """Test that public clients (token_endpoint_auth_method='none') don't receive client_secret."""
        response = await client.post(
            "/v1/oauth2/register",
            json={
                "client_name": "Test Public Client",
                "redirect_uris": ["https://example.com/callback"],
                "token_endpoint_auth_method": "none",
                "scope": "openid email",
            },
        )

        assert response.status_code == 201
        json = response.json()

        # Verify the client was registered as public
        assert json["token_endpoint_auth_method"] == "none"

        # Temporary workaround: client_secret should NOT be in the response
        assert "client_secret" not in json
        assert "client_secret_expires_at" not in json

        # Other fields should still be present
        assert "client_id" in json
        assert "registration_access_token" in json
        assert json["scope"] == "openid email"

    @pytest.mark.auth(AuthSubjectFixture(subject="user"))
    async def test_writes_hashed_and_encrypted_secrets(
        self, client: AsyncClient, sync_session: Session
    ) -> None:
        response = await client.post(
            "/v1/oauth2/register",
            json={
                "client_name": "Test Client",
                "redirect_uris": ["https://example.com/callback"],
            },
        )

        assert response.status_code == 201
        data = response.json()

        oauth2_client = (
            sync_session.execute(
                select(OAuth2Client).where(OAuth2Client.client_id == data["client_id"])
            )
            .unique()
            .scalar_one()
        )

        assert oauth2_client.client_secret_hash == OAuth2Client.hash_secret(
            data["client_secret"]
        )
        assert oauth2_client.registration_access_token_hash == OAuth2Client.hash_secret(
            data["registration_access_token"]
        )
        assert isinstance(oauth2_client.client_secret_encrypted, EncryptedString)
        assert isinstance(
            oauth2_client.registration_access_token_encrypted, EncryptedString
        )
        assert (
            await oauth2_client.client_secret_encrypted.decrypt(
                id=str(oauth2_client.id)
            )
            == data["client_secret"]
        )
        assert (
            await oauth2_client.registration_access_token_encrypted.decrypt(
                id=str(oauth2_client.id)
            )
            == data["registration_access_token"]
        )


@pytest.mark.asyncio
class TestOAuth2ConfigureGet:
    async def test_unauthenticated(
        self, client: AsyncClient, oauth2_client: OAuth2Client
    ) -> None:
        response = await client.get(f"/v1/oauth2/register/{oauth2_client.client_id}")

        assert response.status_code == 400

    async def test_token_not_existing_client(self, client: AsyncClient) -> None:
        response = await client.get(
            "/v1/oauth2/register/INVALID_CLIENT_ID",
            headers={"Authorization": "Bearer REGISTRATION_ACCESS_TOKEN"},
        )

        assert response.status_code == 401

    async def test_token_invalid_token(
        self, client: AsyncClient, oauth2_client: OAuth2Client
    ) -> None:
        response = await client.get(
            f"/v1/oauth2/register/{oauth2_client.client_id}",
            headers={"Authorization": "Bearer INVALID_REGISTRATION_ACCESS_TOKEN"},
        )

        assert response.status_code == 401

    async def test_token_valid(
        self, client: AsyncClient, oauth2_client: OAuth2Client
    ) -> None:
        response = await client.get(
            f"/v1/oauth2/register/{oauth2_client.client_id}",
            headers={"Authorization": f"Bearer {'outception_crt_123'}"},
        )

        assert response.status_code == 200
        json = response.json()
        assert json["client_id"] == oauth2_client.client_id
        for value in json.values():
            assert value is not None

    @pytest.mark.auth(AuthSubjectFixture(subject="user_second"))
    async def test_user_not_owner(
        self, client: AsyncClient, oauth2_client: OAuth2Client
    ) -> None:
        response = await client.get(f"/v1/oauth2/register/{oauth2_client.client_id}")

        assert response.status_code == 401

    @pytest.mark.auth
    async def test_user_valid(
        self, client: AsyncClient, oauth2_client: OAuth2Client
    ) -> None:
        response = await client.get(f"/v1/oauth2/register/{oauth2_client.client_id}")

        assert response.status_code == 200
        json = response.json()
        assert json["client_id"] == oauth2_client.client_id
        for value in json.values():
            assert value is not None

    async def test_public_client_no_secret(
        self, client: AsyncClient, public_oauth2_client: OAuth2Client
    ) -> None:
        """Test that public clients don't receive client_secret when retrieving config."""
        response = await client.get(
            f"/v1/oauth2/register/{public_oauth2_client.client_id}",
            headers={"Authorization": f"Bearer {'outception_crt_123'}"},
        )

        assert response.status_code == 200
        json = response.json()

        # Verify the client is public
        assert json["token_endpoint_auth_method"] == "none"

        # Temporary workaround: client_secret should NOT be in the response
        assert "client_secret" not in json
        assert "client_secret_expires_at" not in json

        # Other fields should still be present
        assert json["client_id"] == public_oauth2_client.client_id
        assert "registration_access_token" in json


@pytest.mark.asyncio
class TestOAuth2ConfigurePut:
    async def test_token_valid(
        self, client: AsyncClient, oauth2_client: OAuth2Client
    ) -> None:
        response = await client.put(
            f"/v1/oauth2/register/{oauth2_client.client_id}",
            headers={"Authorization": f"Bearer {'outception_crt_123'}"},
            json={
                "client_id": oauth2_client.client_id,
                "client_name": "Test Client Updated",
                "redirect_uris": ["https://example.com/callback"],
            },
        )

        assert response.status_code == 200
        json = response.json()
        assert json["client_id"] == oauth2_client.client_id
        assert json["client_name"] == "Test Client Updated"
        assert json["redirect_uris"] == ["https://example.com/callback"]
        for value in json.values():
            assert value is not None

    @pytest.mark.auth
    async def test_user_valid(
        self, client: AsyncClient, oauth2_client: OAuth2Client
    ) -> None:
        response = await client.put(
            f"/v1/oauth2/register/{oauth2_client.client_id}",
            json={
                "client_id": oauth2_client.client_id,
                "client_name": "Test Client Updated",
                "redirect_uris": ["https://example.com/callback"],
            },
        )

        assert response.status_code == 200
        json = response.json()
        assert json["client_id"] == oauth2_client.client_id
        assert json["client_name"] == "Test Client Updated"
        assert json["redirect_uris"] == ["https://example.com/callback"]
        for value in json.values():
            assert value is not None


@pytest.mark.asyncio
class TestOAuth2ConfigureDelete:
    async def test_token_valid(
        self, client: AsyncClient, oauth2_client: OAuth2Client
    ) -> None:
        response = await client.delete(
            f"/v1/oauth2/register/{oauth2_client.client_id}",
            headers={"Authorization": f"Bearer {'outception_crt_123'}"},
        )

        assert response.status_code == 204

    @pytest.mark.auth
    async def test_user_valid(
        self, client: AsyncClient, oauth2_client: OAuth2Client
    ) -> None:
        response = await client.delete(f"/v1/oauth2/register/{oauth2_client.client_id}")

        assert response.status_code == 204

    async def test_revokes_client_tokens(
        self,
        client: AsyncClient,
        oauth2_client: OAuth2Client,
        user: User,
        save_fixture: SaveFixture,
        sync_session: Session,
    ) -> None:
        other_client = OAuth2Client(client_id="outception_ci_other", user_id=user.id)
        other_client.set_client_metadata(oauth2_client.client_metadata)
        await save_fixture(other_client)
        tokens = [
            await create_oauth2_token(
                save_fixture,
                client=token_client,
                access_token=f"outception_at_{index}",
                refresh_token=f"outception_rt_{index}",
                scopes=["openid"],
                user=user,
            )
            for index, token_client in enumerate(
                (oauth2_client, oauth2_client, other_client)
            )
        ]

        response = await client.delete(
            f"/v1/oauth2/register/{oauth2_client.client_id}",
            headers={"Authorization": "Bearer outception_crt_123"},
        )

        assert response.status_code == 204
        for token in tokens[:2]:
            saved_token = sync_session.get(OAuth2Token, token.id)
            assert saved_token is not None
            assert saved_token.access_token_revoked_at > 0
            assert saved_token.refresh_token_revoked_at > 0
        other_token = sync_session.get(OAuth2Token, tokens[2].id)
        assert other_token is not None
        assert other_token.access_token_revoked_at == 0
        assert other_token.refresh_token_revoked_at == 0


@pytest.mark.asyncio
class TestOAuth2Authorize:
    async def test_unauthenticated(
        self, client: AsyncClient, oauth2_client: OAuth2Client
    ) -> None:
        params = {
            "client_id": oauth2_client.client_id,
            "response_type": "code",
            "redirect_uri": "http://127.0.0.1:8000/docs/oauth2-redirect",
            "scope": "openid profile email",
        }
        response = await client.get("/v1/oauth2/authorize", params=params)

        assert response.status_code == 401

    async def test_unauthenticated_prompt_none(
        self, client: AsyncClient, oauth2_client: OAuth2Client
    ) -> None:
        params = {
            "client_id": oauth2_client.client_id,
            "response_type": "code",
            "redirect_uri": "http://127.0.0.1:8000/docs/oauth2-redirect",
            "scope": "openid profile email",
            "prompt": "none",
        }
        response = await client.get("/v1/oauth2/authorize", params=params)

        assert response.status_code == 302
        location = response.headers["location"]
        assert "error=login_required" in location

    @pytest.mark.auth
    async def test_authenticated_invalid_sub_type(
        self, client: AsyncClient, oauth2_client: OAuth2Client
    ) -> None:
        params = {
            "client_id": oauth2_client.client_id,
            "response_type": "code",
            "redirect_uri": "http://127.0.0.1:8000/docs/oauth2-redirect",
            "scope": "openid profile email",
            "sub_type": "foo",
        }
        response = await client.get("/v1/oauth2/authorize", params=params)

        assert response.status_code == 400

    @pytest.mark.auth
    @pytest.mark.parametrize("input_sub_type", [None, "user"])
    async def test_authenticated(
        self,
        input_sub_type: str | None,
        client: AsyncClient,
        oauth2_client: OAuth2Client,
    ) -> None:
        params = {
            "client_id": oauth2_client.client_id,
            "response_type": "code",
            "redirect_uri": "http://127.0.0.1:8000/docs/oauth2-redirect",
            "scope": "openid profile email",
        }
        if input_sub_type is not None:
            params["sub_type"] = input_sub_type
        response = await client.get("/v1/oauth2/authorize", params=params)

        assert response.status_code == 200

        json = response.json()
        assert json["client"]["client_id"] == oauth2_client.client_id
        assert set(json["scopes"]) == {"openid", "profile", "email"}
        assert json["sub_type"] == "user"

    @pytest.mark.auth
    async def test_dynamically_registered_client_defaults_to_user(
        self, client: AsyncClient
    ) -> None:
        """`default_sub_type` is not an RFC 7591 registered claim, so it's
        stripped from the metadata of dynamically-registered clients. The
        authorize flow must then fall back to a user-scoped grant."""
        register_response = await client.post(
            "/v1/oauth2/register",
            json={
                "client_name": "Test DCR Client",
                "redirect_uris": ["https://example.com/callback"],
                "scope": "openid profile email",
            },
        )
        assert register_response.status_code == 201
        client_id = register_response.json()["client_id"]

        params = {
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": "https://example.com/callback",
            "scope": "openid profile email",
        }
        response = await client.get("/v1/oauth2/authorize", params=params)

        assert response.status_code == 200
        assert response.json()["sub_type"] == "user"

    @pytest.mark.auth
    async def test_authenticated_prompt_login(
        self, client: AsyncClient, oauth2_client: OAuth2Client
    ) -> None:
        params = {
            "client_id": oauth2_client.client_id,
            "response_type": "code",
            "redirect_uri": "http://127.0.0.1:8000/docs/oauth2-redirect",
            "scope": "openid profile email",
            "prompt": "login",
        }
        response = await client.get("/v1/oauth2/authorize", params=params)

        assert response.status_code == 401

    @pytest.mark.auth
    async def test_no_scope(
        self, client: AsyncClient, oauth2_client: OAuth2Client
    ) -> None:
        params = {
            "client_id": oauth2_client.client_id,
            "response_type": "code",
            "redirect_uri": "http://127.0.0.1:8000/docs/oauth2-redirect",
        }
        response = await client.get("/v1/oauth2/authorize", params=params)

        assert response.status_code == 200

        json = response.json()
        assert json["client"]["client_id"] == oauth2_client.client_id
        assert set(json["scopes"]) == set(oauth2_client.scope.split(" "))

    @pytest.mark.auth
    @pytest.mark.parametrize("prompt", [None, "none", "consent"])
    async def test_no_scope_first_party_client(
        self,
        prompt: str | None,
        client: AsyncClient,
        first_party_oauth2_client: OAuth2Client,
    ) -> None:
        params = {
            "client_id": first_party_oauth2_client.client_id,
            "response_type": "code",
            "redirect_uri": "http://127.0.0.1:8000/docs/oauth2-redirect",
        }
        if prompt is not None:
            params["prompt"] = prompt
        response = await client.get("/v1/oauth2/authorize", params=params)

        assert response.status_code == 302
        location = response.headers["location"]
        assert location.startswith(params["redirect_uri"])
        assert "code=" in location
        assert parse_qs(urlparse(location).query)["iss"] == [settings.BASE_URL]

    @pytest.mark.auth
    async def test_new_scope(
        self,
        save_fixture: SaveFixture,
        client: AsyncClient,
        user: User,
        oauth2_client: OAuth2Client,
    ) -> None:
        await create_oauth2_grant(
            save_fixture,
            client=oauth2_client,
            user=user,
            scopes=["openid", "profile"],
        )
        params = {
            "client_id": oauth2_client.client_id,
            "response_type": "code",
            "redirect_uri": "http://127.0.0.1:8000/docs/oauth2-redirect",
            "scope": "openid profile email",
        }
        response = await client.get("/v1/oauth2/authorize", params=params)

        assert response.status_code == 200

        json = response.json()
        assert json["client"]["client_id"] == oauth2_client.client_id
        assert set(json["scopes"]) == {"openid", "profile", "email"}

    @pytest.mark.auth
    @pytest.mark.parametrize("prompt", [None, "none", "consent"])
    async def test_new_scope_first_party_client(
        self,
        prompt: str | None,
        sync_session: Session,
        save_fixture: SaveFixture,
        client: AsyncClient,
        user: User,
        first_party_oauth2_client: OAuth2Client,
    ) -> None:
        grant = await create_oauth2_grant(
            save_fixture,
            client=first_party_oauth2_client,
            user=user,
            scopes=["openid", "profile"],
        )
        params = {
            "client_id": first_party_oauth2_client.client_id,
            "response_type": "code",
            "redirect_uri": "http://127.0.0.1:8000/docs/oauth2-redirect",
        }
        if prompt is not None:
            params["prompt"] = prompt
        response = await client.get("/v1/oauth2/authorize", params=params)

        assert response.status_code == 302
        location = response.headers["location"]
        assert location.startswith(params["redirect_uri"])
        assert "code=" in location

        updated_grant = sync_session.get(OAuth2Grant, grant.id)
        assert updated_grant is not None
        assert set(updated_grant.scopes) == set(
            first_party_oauth2_client.scope.split(" ")
        )

    @pytest.mark.auth
    @pytest.mark.parametrize("scope", ["openid", "openid profile email"])
    async def test_granted(
        self,
        scope: str,
        save_fixture: SaveFixture,
        client: AsyncClient,
        user: User,
        oauth2_client: OAuth2Client,
    ) -> None:
        await create_oauth2_grant(
            save_fixture,
            client=oauth2_client,
            user=user,
            scopes=["openid", "profile", "email"],
        )
        params = {
            "client_id": oauth2_client.client_id,
            "response_type": "code",
            "redirect_uri": "http://127.0.0.1:8000/docs/oauth2-redirect",
            "scope": scope,
            "sub_type": "user",
        }
        response = await client.get("/v1/oauth2/authorize", params=params)

        assert response.status_code == 302
        location = response.headers["location"]
        assert location.startswith(params["redirect_uri"])
        assert "code=" in location

    @pytest.mark.auth
    async def test_granted_prompt_consent(
        self,
        save_fixture: SaveFixture,
        client: AsyncClient,
        user: User,
        oauth2_client: OAuth2Client,
    ) -> None:
        await create_oauth2_grant(
            save_fixture,
            client=oauth2_client,
            user=user,
            scopes=["openid", "profile", "email"],
        )
        params = {
            "client_id": oauth2_client.client_id,
            "response_type": "code",
            "redirect_uri": "http://127.0.0.1:8000/docs/oauth2-redirect",
            "scope": "openid profile email",
            "prompt": "consent",
            "sub_type": "user",
        }
        response = await client.get("/v1/oauth2/authorize", params=params)

        json = response.json()
        assert json["client"]["client_id"] == oauth2_client.client_id
        assert set(json["scopes"]) == {"openid", "profile", "email"}

    @pytest.mark.auth
    @pytest.mark.parametrize("granted_scope", [None, ["openid", "profile"]])
    async def test_not_granted_prompt_none(
        self,
        save_fixture: SaveFixture,
        granted_scope: list[str],
        client: AsyncClient,
        oauth2_client: OAuth2Client,
    ) -> None:
        if granted_scope is not None:
            await create_oauth2_grant(
                save_fixture,
                client=oauth2_client,
                user=oauth2_client.user,
                scopes=granted_scope,
            )

        params = {
            "client_id": oauth2_client.client_id,
            "response_type": "code",
            "redirect_uri": "http://127.0.0.1:8000/docs/oauth2-redirect",
            "scope": "openid profile email",
            "prompt": "none",
            "sub_type": "user",
        }
        response = await client.get("/v1/oauth2/authorize", params=params)

        assert response.status_code == 302
        location = response.headers["location"]
        assert "error=consent_required" in location


@pytest.mark.asyncio
class TestOAuth2Consent:
    async def test_unauthenticated(self, client: AsyncClient) -> None:
        response = await client.post("/v1/oauth2/consent")

        assert response.status_code == 401

    @pytest.mark.auth
    async def test_deny(self, client: AsyncClient, oauth2_client: OAuth2Client) -> None:
        params = {
            "client_id": oauth2_client.client_id,
            "response_type": "code",
            "redirect_uri": "http://127.0.0.1:8000/docs/oauth2-redirect",
            "scope": "openid profile email",
            "sub_type": "user",
        }
        response = await client.post(
            "/v1/oauth2/consent", params=params, data={"action": "deny"}
        )

        assert response.status_code == 302
        location = response.headers["location"]
        assert "error=access_denied" in location
        assert parse_qs(urlparse(location).query)["iss"] == [settings.BASE_URL]

    @pytest.mark.auth
    async def test_allow(
        self,
        client: AsyncClient,
        user: User,
        oauth2_client: OAuth2Client,
        sync_session: Session,
    ) -> None:
        params = {
            "client_id": oauth2_client.client_id,
            "response_type": "code",
            "redirect_uri": "http://127.0.0.1:8000/docs/oauth2-redirect",
            "scope": "openid profile email",
            "sub_type": "user",
        }
        response = await client.post(
            "/v1/oauth2/consent", params=params, data={"action": "allow"}
        )

        assert response.status_code == 302
        location = response.headers["location"]
        assert location.startswith(params["redirect_uri"])
        assert "code=" in location

        grant = oauth2_grant_service._get_by_sub_and_client_id(
            sync_session,
            sub_type=SubType.user,
            sub_id=user.id,
            client_id=oauth2_client.client_id,
        )
        assert grant is not None
        assert grant.scopes == ["openid", "profile", "email"]

    @pytest.mark.auth
    async def test_state_echoed_on_invalid_scope_redirect(
        self, client: AsyncClient, oauth2_client: OAuth2Client
    ) -> None:
        params = {
            "client_id": oauth2_client.client_id,
            "response_type": "code",
            "redirect_uri": "http://127.0.0.1:8000/docs/oauth2-redirect",
            "scope": "openid profile email invalid_scope_xyz",
            "sub_type": "user",
            "state": "xyz123",
        }
        response = await client.post(
            "/v1/oauth2/consent", params=params, data={"action": "allow"}
        )

        assert response.status_code == 302
        location = response.headers["location"]
        query = parse_qs(urlparse(location).query)
        assert query["error"] == ["invalid_scope"]
        assert query["state"] == ["xyz123"]
        assert query["iss"] == [settings.BASE_URL]

    @pytest.mark.auth
    async def test_state_echoed_on_unsupported_response_type_redirect(
        self, client: AsyncClient, oauth2_client: OAuth2Client
    ) -> None:
        params = {
            "client_id": oauth2_client.client_id,
            "response_type": "token",
            "redirect_uri": "http://127.0.0.1:8000/docs/oauth2-redirect",
            "scope": "openid profile email",
            "sub_type": "user",
            "state": "abc456",
        }
        response = await client.post(
            "/v1/oauth2/consent", params=params, data={"action": "allow"}
        )

        assert response.status_code == 302
        location = response.headers["location"]
        query = parse_qs(urlparse(location).query)
        assert query["error"] == ["unsupported_response_type"]
        assert query["state"] == ["abc456"]

    @pytest.mark.auth
    async def test_state_echoed_on_invalid_request_json(
        self, client: AsyncClient, oauth2_client: OAuth2Client
    ) -> None:
        params = {
            "client_id": oauth2_client.client_id,
            "response_type": "code",
            "redirect_uri": "http://127.0.0.1:8000/docs/oauth2-redirect",
            "scope": "openid profile email",
            "sub_type": "foo",
            "state": "jsonstate",
        }
        response = await client.post(
            "/v1/oauth2/consent", params=params, data={"action": "allow"}
        )

        assert response.status_code == 400
        body = response.json()
        assert body["error"] == "invalid_request"
        assert body["state"] == "jsonstate"


@pytest.mark.asyncio
class TestOAuth2Token:
    async def test_authorization_code_sub_user(
        self,
        save_fixture: SaveFixture,
        client: AsyncClient,
        user: User,
        oauth2_client: OAuth2Client,
    ) -> None:
        await create_oauth2_authorization_code(
            save_fixture,
            client=oauth2_client,
            code="CODE",
            scopes=["openid", "profile", "email"],
            redirect_uri="http://127.0.0.1:8000/docs/oauth2-redirect",
            user=user,
        )

        data = {
            "grant_type": "authorization_code",
            "code": "CODE",
            "client_id": oauth2_client.client_id,
            "client_secret": "outception_cs_123",
            "redirect_uri": "http://127.0.0.1:8000/docs/oauth2-redirect",
        }

        response = await client.post("/v1/oauth2/token", data=data)

        assert response.status_code == 200
        json = response.json()

        access_token = json["access_token"]
        assert access_token.startswith("outception_at_u_")
        refresh_token = json["refresh_token"]
        assert refresh_token.startswith("outception_rt_u_")

    async def test_authorization_code_public_client(
        self,
        save_fixture: SaveFixture,
        client: AsyncClient,
        user: User,
        public_oauth2_client: OAuth2Client,
    ) -> None:
        code_verifier = "A" * 43
        await create_oauth2_authorization_code(
            save_fixture,
            client=public_oauth2_client,
            code="CODE",
            scopes=["openid", "profile", "email"],
            redirect_uri="http://127.0.0.1:8000/docs/oauth2-redirect",
            user=user,
            code_verifier=code_verifier,
            code_challenge_method="S256",
        )

        data = {
            "grant_type": "authorization_code",
            "code": "CODE",
            "client_id": public_oauth2_client.client_id,
            "code_verifier": code_verifier,
            "redirect_uri": "http://127.0.0.1:8000/docs/oauth2-redirect",
        }

        response = await client.post("/v1/oauth2/token", data=data)

        assert response.status_code == 200
        json = response.json()

        access_token = json["access_token"]
        assert access_token.startswith("outception_at_u_")
        refresh_token = json["refresh_token"]
        assert refresh_token.startswith("outception_rt_u_")

    async def test_authorization_code_id_token_signed_with_published_key(
        self,
        save_fixture: SaveFixture,
        client: AsyncClient,
        user: User,
        oauth2_client: OAuth2Client,
    ) -> None:
        await create_oauth2_authorization_code(
            save_fixture,
            client=oauth2_client,
            code="CODE",
            scopes=["openid", "profile", "email"],
            redirect_uri="http://127.0.0.1:8000/docs/oauth2-redirect",
            user=user,
        )

        data = {
            "grant_type": "authorization_code",
            "code": "CODE",
            "client_id": oauth2_client.client_id,
            "client_secret": "outception_cs_123",
            "redirect_uri": "http://127.0.0.1:8000/docs/oauth2-redirect",
        }

        response = await client.post("/v1/oauth2/token", data=data)

        assert response.status_code == 200
        id_token = response.json()["id_token"]

        header = jwt.get_unverified_header(id_token)
        assert header["typ"] == "JWT"
        assert header["alg"] == "RS256"
        assert header["kid"] == settings.LOCAL_JWK_KID

        jwks_response = await client.get("/.well-known/jwks.json")
        signing_key = jwt.PyJWKSet.from_dict(jwks_response.json())[header["kid"]]
        claims = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=[header["alg"]],
            audience=oauth2_client.client_id,
        )

        assert claims["iss"] == settings.BASE_URL
        assert claims["sub"] == str(user.id)
        assert "kid" not in claims

    async def test_authorization_code_revoked_public_client(
        self,
        save_fixture: SaveFixture,
        sync_session: Session,
        client: AsyncClient,
        user: User,
        public_oauth2_client: OAuth2Client,
    ) -> None:
        code_verifier = "A" * 43
        authorization_code = await create_oauth2_authorization_code(
            save_fixture,
            client=public_oauth2_client,
            code="CODE",
            scopes=["openid", "profile", "email"],
            redirect_uri="http://127.0.0.1:8000/docs/oauth2-redirect",
            user=user,
            code_verifier=code_verifier,
            code_challenge_method="S256",
        )
        authorization_code.set_deleted_at()
        sync_session.add(authorization_code)
        sync_session.flush()
        sync_session.expunge(authorization_code)

        data = {
            "grant_type": "authorization_code",
            "code": "CODE",
            "client_id": public_oauth2_client.client_id,
            "code_verifier": code_verifier,
            "redirect_uri": "http://127.0.0.1:8000/docs/oauth2-redirect",
        }

        response = await client.post("/v1/oauth2/token", data=data)

        assert response.status_code == 400
        json = response.json()
        assert "access_token" not in json
        assert "refresh_token" not in json

    async def test_refresh_token_sub_user(
        self,
        save_fixture: SaveFixture,
        client: AsyncClient,
        user: User,
        oauth2_client: OAuth2Client,
    ) -> None:
        await create_oauth2_token(
            save_fixture,
            client=oauth2_client,
            access_token="ACCESS_TOKEN",
            refresh_token="REFRESH_TOKEN",
            scopes=["openid", "profile", "email"],
            user=user,
        )

        data = {
            "grant_type": "refresh_token",
            "refresh_token": "REFRESH_TOKEN",
            "client_id": oauth2_client.client_id,
            "client_secret": "outception_cs_123",
        }

        response = await client.post("/v1/oauth2/token", data=data)

        assert response.status_code == 200
        json = response.json()

        access_token = json["access_token"]
        assert access_token.startswith("outception_at_u_")
        refresh_token = json["refresh_token"]
        assert refresh_token.startswith("outception_rt_u_")

    async def test_refresh_token_unauthenticated_private_client(
        self,
        save_fixture: SaveFixture,
        client: AsyncClient,
        user: User,
        oauth2_client: OAuth2Client,
    ) -> None:
        await create_oauth2_token(
            save_fixture,
            client=oauth2_client,
            access_token="ACCESS_TOKEN",
            refresh_token="REFRESH_TOKEN",
            scopes=["openid", "profile", "email"],
            user=user,
        )

        data = {
            "grant_type": "refresh_token",
            "refresh_token": "REFRESH_TOKEN",
            "client_id": oauth2_client.client_id,
        }

        response = await client.post("/v1/oauth2/token", data=data)

        assert response.status_code == 401

    async def test_refresh_token_public_client(
        self,
        save_fixture: SaveFixture,
        client: AsyncClient,
        user: User,
        public_oauth2_client: OAuth2Client,
    ) -> None:
        await create_oauth2_token(
            save_fixture,
            client=public_oauth2_client,
            access_token="ACCESS_TOKEN",
            refresh_token="REFRESH_TOKEN",
            scopes=["openid", "profile", "email"],
            user=user,
        )

        data = {
            "grant_type": "refresh_token",
            "refresh_token": "REFRESH_TOKEN",
            "client_id": public_oauth2_client.client_id,
        }

        response = await client.post("/v1/oauth2/token", data=data)

        assert response.status_code == 200
        json = response.json()

        access_token = json["access_token"]
        assert access_token.startswith("outception_at_u_")
        refresh_token = json["refresh_token"]
        assert refresh_token.startswith("outception_rt_u_")

    @pytest.mark.parametrize(
        "payload",
        [
            pytest.param({"grant_type": "web"}, id="missing session_token"),
            pytest.param(
                {
                    "grant_type": "web",
                    "session_token": "TOKEN",
                    "sub_type": "invalid",
                },
                id="invalid sub_type",
            ),
            pytest.param(
                {
                    "grant_type": "web",
                    "session_token": "TOKEN",
                    "sub_type": "user",
                    "sub": "USER_ID",
                },
                id="sub set for user sub_type",
            ),
            pytest.param(
                {
                    "grant_type": "web",
                    "session_token": "TOKEN",
                    "sub_type": "foo",
                },
                id="unknown sub_type",
            ),
            pytest.param(
                {
                    "grant_type": "web",
                    "session_token": "TOKEN",
                    "sub_type": "foo",
                    "sub": "ORGANIZATION_ID",
                },
                id="unknown sub_type with sub",
            ),
            pytest.param(
                {
                    "grant_type": "web",
                    "session_token": "TOKEN",
                    "sub_type": "user",
                    "scope": "invalid_scope",
                },
                id="invalid scope",
            ),
        ],
    )
    async def test_web_grant_invalid_request(
        self,
        payload: dict[str, str],
        save_fixture: SaveFixture,
        client: AsyncClient,
        user: User,
        web_grant_oauth2_client: OAuth2Client,
    ) -> None:
        data = {
            **payload,
            "client_id": web_grant_oauth2_client.client_id,
            "client_secret": "outception_cs_123",
        }

        response = await client.post("/v1/oauth2/token", data=data)

        assert response.status_code == 400

    async def test_web_grant_rehashes_a_session_under_a_retired_secret(
        self,
        save_fixture: SaveFixture,
        sync_session: Session,
        client: AsyncClient,
        user: User,
        web_grant_oauth2_client: OAuth2Client,
        mocker: MockerFixture,
    ) -> None:
        """The cookie path rehashes on every request; this one is the only way
        in for a session that never touches the dashboard."""
        secrets = {"k1": "retired", "k2": "current"}
        mocker.patch(
            "outception.kit.crypto.get_hash_secrets",
            return_value=HashSecrets(secrets, "k1", "legacy"),
        )
        # The fixture hashed the client secret before the patch.
        await web_grant_oauth2_client.set_client_secret("outception_cs_123")
        await save_fixture(web_grant_oauth2_client)
        token, token_hash = generate_token_hash_pair(prefix=USER_SESSION_TOKEN_PREFIX)
        user_session = UserSession(
            token=token_hash,
            user_agent="tests",
            user=user,
            scopes=set(Scope),
            expires_at=utc_now() + timedelta(seconds=60),
        )
        await save_fixture(user_session)

        mocker.patch(
            "outception.kit.crypto.get_hash_secrets",
            return_value=HashSecrets(secrets, "k2", "legacy"),
        )
        data = {
            "grant_type": "web",
            "session_token": token,
            "client_id": web_grant_oauth2_client.client_id,
            "client_secret": "outception_cs_123",
        }

        response = await client.post("/v1/oauth2/token", data=data)

        assert response.status_code == 200
        refreshed = sync_session.get(UserSession, user_session.id)
        assert refreshed is not None
        assert refreshed.token == get_token_hash(token)

    async def test_web_grant_not_allowed_client(
        self,
        save_fixture: SaveFixture,
        client: AsyncClient,
        user: User,
        oauth2_client: OAuth2Client,
    ) -> None:
        token, token_hash = generate_token_hash_pair(prefix=USER_SESSION_TOKEN_PREFIX)
        user_session = UserSession(
            token=token_hash,
            user_agent="tests",
            user=user,
            scopes=set(Scope),
            expires_at=utc_now() + timedelta(seconds=60),
        )
        await save_fixture(user_session)

        data = {
            "grant_type": "web",
            "session_token": token,
            "client_id": oauth2_client.client_id,
            "client_secret": "outception_cs_123",
        }

        response = await client.post("/v1/oauth2/token", data=data)

        assert response.status_code == 400

    async def test_web_grant_sub_user(
        self,
        save_fixture: SaveFixture,
        client: AsyncClient,
        user: User,
        web_grant_oauth2_client: OAuth2Client,
    ) -> None:
        token, token_hash = generate_token_hash_pair(prefix=USER_SESSION_TOKEN_PREFIX)
        user_session = UserSession(
            token=token_hash,
            user_agent="tests",
            user=user,
            scopes=set(Scope),
            expires_at=utc_now() + timedelta(seconds=60),
        )
        await save_fixture(user_session)

        data = {
            "grant_type": "web",
            "session_token": token,
            "client_id": web_grant_oauth2_client.client_id,
            "client_secret": "outception_cs_123",
        }

        response = await client.post("/v1/oauth2/token", data=data)

        assert response.status_code == 200
        json = response.json()

        access_token = json["access_token"]
        assert access_token.startswith("outception_at_u_")
        assert "refresh_token" not in json
