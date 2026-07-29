from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from outception.email.schemas import OAuth2LeakedClientEmail
from outception.enums import TokenType
from outception.models import OAuth2Client
from outception.oauth2.service.oauth2_client import (
    oauth2_client as oauth2_client_service,
)
from outception.postgres import AsyncSession


@pytest.fixture(autouse=True)
def enqueue_email_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.patch(
        "outception.oauth2.service.oauth2_client.enqueue_email_template", autospec=True
    )


@pytest.mark.asyncio
class TestRevokeLeaked:
    @pytest.mark.parametrize(
        ("token", "token_type"),
        [
            ("outception_cs_123", TokenType.client_secret),
            ("outception_crt_123", TokenType.client_registration_token),
        ],
    )
    async def test_false_positive(
        self,
        token: str,
        token_type: TokenType,
        session: AsyncSession,
        enqueue_email_mock: MagicMock,
    ) -> None:
        result = await oauth2_client_service.revoke_leaked(
            session, token, token_type, notifier="github", url="https://github.com"
        )
        assert result is False

        enqueue_email_mock.assert_not_called()

    @pytest.mark.parametrize(
        "token_type",
        [
            TokenType.client_secret,
            TokenType.client_registration_token,
        ],
    )
    async def test_true_positive(
        self,
        token_type: TokenType,
        session: AsyncSession,
        oauth2_client: OAuth2Client,
        enqueue_email_mock: MagicMock,
    ) -> None:
        token = (
            # The stored client_secret is a hash; the "leaked" value GitHub would
            # report (and revoke_leaked matches on) is the plaintext.
            "outception_cs_123"
            if token_type == TokenType.client_secret
            else oauth2_client.registration_access_token
        )

        result = await oauth2_client_service.revoke_leaked(
            session, token, token_type, notifier="github", url="https://github.com"
        )
        assert result is True

        updated_oauth2_client = await session.get(OAuth2Client, oauth2_client.id)
        assert updated_oauth2_client is not None

        if token_type == TokenType.client_secret:
            assert updated_oauth2_client.client_secret != token
        else:
            assert updated_oauth2_client.registration_access_token != token

        enqueue_email_mock.assert_called_once()
        assert isinstance(enqueue_email_mock.call_args[0][0], OAuth2LeakedClientEmail)
