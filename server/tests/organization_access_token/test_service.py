from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from outception.auth.models import AuthSubject
from outception.auth.scope import Scope
from outception.config import settings
from outception.email.schemas import OrganizationAccessTokenLeakedEmail
from outception.enums import TokenType
from outception.exceptions import OutceptionRequestValidationError
from outception.kit.crypto import get_token_hash
from outception.kit.utils import utc_now
from outception.models import (
    Organization,
    OrganizationAccessToken,
    PersonalAccessToken,
    User,
    UserOrganization,
)
from outception.organization_access_token.schemas import (
    AvailableScope,
    OrganizationAccessTokenCreate,
)
from outception.organization_access_token.service import (
    organization_access_token as organization_access_token_service,
)
from outception.postgres import AsyncSession
from tests.fixtures.database import SaveFixture


@pytest.fixture(autouse=True)
def enqueue_email_mock(mocker: MockerFixture) -> MagicMock:
    return mocker.patch(
        "outception.organization_access_token.service.enqueue_email_template",
        autospec=True,
    )


@pytest.mark.asyncio
class TestRevokeLeaked:
    async def test_false_positive(
        self, session: AsyncSession, enqueue_email_mock: MagicMock
    ) -> None:
        result = await organization_access_token_service.revoke_leaked(
            session,
            "outception_pat_123",
            TokenType.organization_access_token,
            notifier="github",
            url="https://github.com",
        )
        assert result is False

        enqueue_email_mock.assert_not_called()

    async def test_true_positive(
        self,
        save_fixture: SaveFixture,
        session: AsyncSession,
        organization: Organization,
        user_organization: UserOrganization,
        enqueue_email_mock: MagicMock,
    ) -> None:
        token_hash = get_token_hash("outception_pat_123", secret=settings.SECRET)
        organization_access_token = OrganizationAccessToken(
            comment="Test",
            token=token_hash,
            organization=organization,
            expires_at=utc_now() + timedelta(days=1),
            scope="openid",
        )
        await save_fixture(organization_access_token)

        result = await organization_access_token_service.revoke_leaked(
            session,
            "outception_pat_123",
            TokenType.organization_access_token,
            notifier="github",
            url="https://github.com",
        )
        assert result is True

        updated_organization_access_token = await session.get(
            OrganizationAccessToken, organization_access_token.id
        )
        assert updated_organization_access_token is not None
        assert updated_organization_access_token.deleted_at is not None

        enqueue_email_mock.assert_called_once()
        assert isinstance(
            enqueue_email_mock.call_args[0][0], OrganizationAccessTokenLeakedEmail
        )


@pytest.mark.asyncio
class TestCreateScopeValidation:
    async def test_pat_caller_cannot_mint_broader_scope(
        self,
        session: AsyncSession,
        user: User,
        organization: Organization,
        user_organization: UserOrganization,
    ) -> None:
        pat_session = MagicMock(spec=PersonalAccessToken)
        auth_subject: AuthSubject[User] = AuthSubject(
            user, {Scope.organization_access_tokens_write}, pat_session
        )

        with pytest.raises(OutceptionRequestValidationError):
            await organization_access_token_service.create(
                session,
                auth_subject,
                OrganizationAccessTokenCreate(
                    organization_id=organization.id,
                    comment="elevated",
                    scopes=[AvailableScope("organizations:read")],
                ),
            )
