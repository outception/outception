from unittest.mock import MagicMock
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from pytest_mock import MockerFixture
from reauth.factors.oauth2.base import OAuth2Account, OAuth2Enrollment
from sqlalchemy import select

from outception.auth.oauth2.google import GoogleFactor
from outception.config import settings
from outception.models import User
from outception.postgres import AsyncSession


async def google_callback(
    client: httpx.AsyncClient,
    mocker: MockerFixture,
    callback_result: OAuth2Enrollment | OAuth2Account,
) -> httpx.Response:
    start = await client.post(
        "/v1/auth/start",
        json={"return_to": "/dashboard"},
    )
    assert start.status_code == 201

    authorize = await client.get("/v1/auth/google/authorize")
    assert authorize.status_code == 303
    state = parse_qs(urlsplit(authorize.headers["location"]).query)["state"][0]

    result: tuple[OAuth2Enrollment | None, OAuth2Account | None, MagicMock]
    if isinstance(callback_result, OAuth2Enrollment):
        result = (callback_result, None, MagicMock())
    else:
        result = (None, callback_result, MagicMock())
    mocker.patch.object(GoogleFactor, "callback", return_value=result)
    mocker.patch.object(GoogleFactor, "get_email", return_value="jane@acme.com")
    mocker.patch.object(GoogleFactor, "enroll", return_value=MagicMock())

    return await client.get(
        "/v1/auth/google/callback", params={"code": "the-code", "state": state}
    )


def google_account() -> OAuth2Account:
    return OAuth2Account(
        provider="google",
        account_id="google-account",
        access_token="access-token",
        expires_at=None,
        refresh_token=None,
        refresh_token_expires_at=None,
        scope=[],
    )


@pytest.mark.asyncio
class TestLoginCallback:
    async def test_new_user(
        self,
        login_client: httpx.AsyncClient,
        mocker: MockerFixture,
        session: AsyncSession,
    ) -> None:
        response = await google_callback(login_client, mocker, google_account())

        assert response.status_code == 303
        assert response.headers["location"] == settings.generate_frontend_url("/auth")
        result = await session.execute(
            select(User).where(User.email == "jane@acme.com")
        )
        assert result.scalars().unique().one_or_none() is not None
