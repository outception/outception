import json
import time

import pytest
from starlette.requests import Request
from starlette.types import Message, Receive, Scope, Send

from outception.auth.middlewares import AuthSubjectMiddleware, get_auth_subject
from outception.auth.models import Anonymous
from outception.auth.service import auth as auth_service
from outception.config import settings
from outception.kit.crypto import get_token_hash
from outception.models import OAuth2Client, OAuth2Token, User
from outception.oauth2.constants import ACCESS_TOKEN_PREFIX
from outception.oauth2.exceptions import InvalidTokenError
from outception.oauth2.sub_type import SubType
from outception.postgres import AsyncSession
from outception.redis import Redis
from tests.fixtures.database import SaveFixture


def _request(headers: list[tuple[bytes, bytes]]) -> Request:
    return Request({"type": "http", "headers": headers})


def _request_with_session_cookie(token: str) -> Request:
    cookie = f"{settings.USER_SESSION_COOKIE_KEY}={token}".encode()
    return _request([(b"cookie", cookie)])


def _request_with_bearer_token(token: str) -> Request:
    header = f"Bearer {token}".encode()
    return _request([(b"authorization", header)])


async def _create_oauth2_token(
    save_fixture: SaveFixture, access_token: str, *, user: User
) -> OAuth2Token:
    client = OAuth2Client(client_id="outception_ci_test")
    await save_fixture(client)
    token = OAuth2Token(
        client_id=client.client_id,
        token_type="bearer",
        access_token=get_token_hash(access_token),
        scope="",
        issued_at=int(time.time()),
        expires_in=3600,
    )
    token.user_id = user.id
    token.sub_type = SubType.user
    await save_fixture(token)
    return token


@pytest.mark.asyncio
class TestGetAuthSubject:
    async def test_anonymous_without_credentials(self, session: AsyncSession) -> None:
        auth_subject = await get_auth_subject(_request([]), session)

        assert isinstance(auth_subject.subject, Anonymous)
        assert auth_subject.session is None

    async def test_user_session_cookie(self, session: AsyncSession, user: User) -> None:
        token, user_session = await auth_service._create_user_session(
            session, user, user_agent="test", scopes=[]
        )

        auth_subject = await get_auth_subject(
            _request_with_session_cookie(token), session
        )

        assert auth_subject.subject == user
        assert auth_subject.session == user_session

    async def test_unknown_session_cookie_is_anonymous(
        self, session: AsyncSession
    ) -> None:
        auth_subject = await get_auth_subject(
            _request_with_session_cookie("outception_us_unknown"), session
        )

        assert isinstance(auth_subject.subject, Anonymous)

    async def test_oauth2_user_token(
        self, save_fixture: SaveFixture, session: AsyncSession, user: User
    ) -> None:
        access_token = f"{ACCESS_TOKEN_PREFIX[SubType.user]}test"
        token = await _create_oauth2_token(save_fixture, access_token, user=user)

        auth_subject = await get_auth_subject(
            _request_with_bearer_token(access_token), session
        )

        assert auth_subject.subject == user
        assert auth_subject.session == token

    async def test_unknown_oauth2_token(self, session: AsyncSession) -> None:
        access_token = f"{ACCESS_TOKEN_PREFIX[SubType.user]}unknown"

        with pytest.raises(InvalidTokenError):
            await get_auth_subject(_request_with_bearer_token(access_token), session)

    async def test_unknown_bearer_prefix(self, session: AsyncSession) -> None:
        with pytest.raises(InvalidTokenError):
            await get_auth_subject(
                _request_with_bearer_token("outception_pat_test"), session
            )


@pytest.mark.asyncio
class TestAuthSubjectMiddleware:
    async def test_invalid_token_returns_401(
        self, session: AsyncSession, redis: Redis
    ) -> None:
        access_token = f"{ACCESS_TOKEN_PREFIX[SubType.user]}unknown"

        async def app(scope: Scope, receive: Receive, send: Send) -> None:
            raise AssertionError("The request should not reach the app")

        messages: list[Message] = []

        async def send(message: Message) -> None:
            messages.append(message)

        async def receive() -> Message:
            return {"type": "http.request", "body": b""}

        request = _request_with_bearer_token(access_token)
        await AuthSubjectMiddleware(app, redis)(
            {**request.scope, "state": {"async_session": session}}, receive, send
        )

        assert messages[0]["status"] == 401
        assert json.loads(messages[1]["body"])["error"] == "invalid_token"
