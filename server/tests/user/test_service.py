import pytest
from sqlalchemy import select

from outception.models import UserOrganization
from outception.models.user_organization import OrganizationRole
from outception.postgres import AsyncSession
from outception.user.service import user as user_service


@pytest.mark.asyncio
class TestGetByEmailOrCreatePersonalOrganization:
    async def _memberships(
        self, session: AsyncSession, user_id: object
    ) -> list[UserOrganization]:
        result = await session.execute(
            select(UserOrganization).where(UserOrganization.user_id == user_id)
        )
        return list(result.scalars().all())

    async def test_new_user_gets_owned_personal_organization(
        self, session: AsyncSession
    ) -> None:
        user, created = await user_service.get_by_email_or_create(
            session, "alice@example.com"
        )
        assert created is True

        memberships = await self._memberships(session, user.id)
        assert len(memberships) == 1
        assert memberships[0].role == OrganizationRole.owner

    async def test_existing_user_without_org_is_backfilled(
        self, session: AsyncSession
    ) -> None:
        user = await user_service.create_by_email(session, "bob@example.com")
        assert await self._memberships(session, user.id) == []

        # A subsequent login back-fills the personal organization.
        same_user, created = await user_service.get_by_email_or_create(
            session, "bob@example.com"
        )
        assert created is False
        assert same_user.id == user.id
        assert len(await self._memberships(session, user.id)) == 1

    async def test_second_login_does_not_create_a_second_org(
        self, session: AsyncSession
    ) -> None:
        user, _ = await user_service.get_by_email_or_create(
            session, "carol@example.com"
        )
        await user_service.get_by_email_or_create(session, "carol@example.com")
        assert len(await self._memberships(session, user.id)) == 1

    async def test_same_local_part_different_domain_gets_unique_slug(
        self, session: AsyncSession
    ) -> None:
        user_a, _ = await user_service.get_by_email_or_create(
            session, "dan@example.com"
        )
        user_b, _ = await user_service.get_by_email_or_create(session, "dan@other.com")
        org_a = (await self._memberships(session, user_a.id))[0].organization_id
        org_b = (await self._memberships(session, user_b.id))[0].organization_id
        assert org_a != org_b
