from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from polar.auth.models import AuthSubject
from polar.auth.scope import Scope
from polar.config import settings
from polar.email.schemas import PersonalAccessTokenLeakedEmail
from polar.enums import TokenType
from polar.exceptions import PolarRequestValidationError
from polar.kit.crypto import get_token_hash
from polar.kit.utils import utc_now
from polar.models import PersonalAccessToken, User
from polar.personal_access_token.schemas import PersonalAccessTokenCreate
from polar.personal_access_token.service import (
    personal_access_token as personal_access_token_service,
)
from polar.postgres import AsyncSession
from tests.fixtures.database import SaveFixture


def _auth(user: User, scopes: set[Scope]) -> AuthSubject[User]:
    return AuthSubject(user, scopes, MagicMock())


@pytest.fixture(autouse=True)
def enqueue_email_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.patch(
        "polar.personal_access_token.service.enqueue_email_template", autospec=True
    )


@pytest.mark.asyncio
class TestRevokeLeaked:
    async def test_false_positive(
        self, session: AsyncSession, enqueue_email_mock: MagicMock
    ) -> None:
        result = await personal_access_token_service.revoke_leaked(
            session,
            "polar_pat_123",
            TokenType.personal_access_token,
            notifier="github",
            url="https://github.com",
        )
        assert result is False

        enqueue_email_mock.assert_not_called()

    async def test_true_positive(
        self,
        save_fixture: SaveFixture,
        session: AsyncSession,
        user: User,
        mocker: MockerFixture,
        enqueue_email_mock: MagicMock,
    ) -> None:
        token_hash = get_token_hash("polar_pat_123", secret=settings.SECRET)
        personal_access_token = PersonalAccessToken(
            comment="Test",
            token=token_hash,
            user_id=user.id,
            expires_at=utc_now() + timedelta(days=1),
            scope="openid",
        )
        await save_fixture(personal_access_token)

        result = await personal_access_token_service.revoke_leaked(
            session,
            "polar_pat_123",
            TokenType.personal_access_token,
            notifier="github",
            url="https://github.com",
        )
        assert result is True

        updated_personal_access_token = await session.get(
            PersonalAccessToken, personal_access_token.id
        )
        assert updated_personal_access_token is not None
        assert updated_personal_access_token.deleted_at is not None

        enqueue_email_mock.assert_called_once()
        assert isinstance(
            enqueue_email_mock.call_args[0][0], PersonalAccessTokenLeakedEmail
        )


@pytest.mark.asyncio
class TestCreate:
    async def test_returns_raw_token_and_stores_only_hash(
        self, session: AsyncSession, user: User
    ) -> None:
        pat, token = await personal_access_token_service.create(
            session,
            _auth(user, {Scope.user_read}),
            PersonalAccessTokenCreate(comment="ci", scopes=[Scope.user_read]),
        )
        assert token.startswith("polar_pat_")
        # Only the hash is persisted; the raw token never is.
        assert pat.token == get_token_hash(token, secret=settings.SECRET)
        assert pat.token != token
        assert pat.scopes == {Scope.user_read}
        assert pat.comment == "ci"
        assert pat.user_id == user.id
        assert pat.expires_at is None

    async def test_rejects_scopes_exceeding_caller(
        self, session: AsyncSession, user: User
    ) -> None:
        # A read-scoped caller must not mint a write-scoped token.
        with pytest.raises(PolarRequestValidationError):
            await personal_access_token_service.create(
                session,
                _auth(user, {Scope.user_read}),
                PersonalAccessTokenCreate(
                    comment="escalate", scopes=[Scope.user_write]
                ),
            )

    async def test_expires_in_sets_expiry(
        self, session: AsyncSession, user: User
    ) -> None:
        before = utc_now()
        pat, _ = await personal_access_token_service.create(
            session,
            _auth(user, {Scope.user_read}),
            PersonalAccessTokenCreate(
                comment="x",
                scopes=[Scope.user_read],
                expires_in=timedelta(days=1),
            ),
        )
        assert pat.expires_at is not None
        assert pat.expires_at > before
