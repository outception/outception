from collections.abc import Sequence
from uuid import UUID

import structlog
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from outception.exceptions import OutceptionError
from outception.kit.utils import utc_now
from outception.models import UserOrganization
from outception.models.user_organization import (
    OrganizationRole,
)
from outception.postgres import AsyncReadSession, AsyncSession, sql

log = structlog.get_logger()


class UserOrganizationError(OutceptionError): ...


class OrganizationWouldHaveNoAdmins(UserOrganizationError):
    def __init__(self, organization_id: UUID) -> None:
        self.organization_id = organization_id
        message = (
            f"Operation rejected: organization {organization_id} would be left "
            f"with no users holding admin or owner role."
        )
        super().__init__(message, 403)


class UserOrganizationService:
    async def list_by_org(
        self, session: AsyncReadSession, org_id: UUID
    ) -> Sequence[UserOrganization]:
        stmt = (
            sql.select(UserOrganization)
            .where(
                UserOrganization.organization_id == org_id,
                UserOrganization.is_deleted.is_(False),
            )
            .options(
                joinedload(UserOrganization.user),
                joinedload(UserOrganization.organization),
            )
        )

        res = await session.execute(stmt)
        return res.scalars().unique().all()

    async def get_by_user_and_org(
        self,
        session: AsyncReadSession,
        user_id: UUID,
        organization_id: UUID,
    ) -> UserOrganization | None:
        stmt = (
            sql.select(UserOrganization)
            .where(
                UserOrganization.user_id == user_id,
                UserOrganization.organization_id == organization_id,
                UserOrganization.is_deleted.is_(False),
            )
            .options(
                joinedload(UserOrganization.user),
                joinedload(UserOrganization.organization),
            )
        )

        res = await session.execute(stmt)
        return res.scalars().unique().one_or_none()

    async def remove_member(
        self,
        session: AsyncSession,
        *,
        user_id: UUID,
        organization_id: UUID,
    ) -> None:
        await self._assert_admin_capability_after_removal(
            session, user_id=user_id, organization_id=organization_id
        )

        existing = await self.get_by_user_and_org(session, user_id, organization_id)

        stmt = (
            sql.update(UserOrganization)
            .where(
                UserOrganization.user_id == user_id,
                UserOrganization.organization_id == organization_id,
                UserOrganization.is_deleted.is_(False),
            )
            .values(deleted_at=utc_now())
            .returning(UserOrganization.user_id)
        )
        result = await session.execute(stmt)
        removed_user_id = result.scalar_one_or_none()
        if removed_user_id is not None:
            log.info(
                "organization.member.removed",
                organization_id=organization_id,
                user_id=user_id,
                role=existing.role if existing is not None else None,
            )

    async def _assert_admin_capability_after_removal(
        self,
        session: AsyncSession,
        *,
        user_id: UUID,
        organization_id: UUID,
    ) -> None:
        """
        Defense-in-depth guard for the admin-capability invariant: an
        organization always has at least one user in `role ∈ {owner, admin}`.

        Rejects only when the removal would actually reduce admin-capable
        count to zero; non-admin-capable removals from a degraded
        organization are still allowed (they don't make the state worse).
        """
        target_role = await session.scalar(
            sql.select(UserOrganization.role).where(
                UserOrganization.organization_id == organization_id,
                UserOrganization.user_id == user_id,
                UserOrganization.is_deleted.is_(False),
            )
        )
        if target_role not in {OrganizationRole.owner, OrganizationRole.admin}:
            return

        other_admin_capable = await session.scalar(
            sql.select(func.count(UserOrganization.user_id)).where(
                UserOrganization.organization_id == organization_id,
                UserOrganization.user_id != user_id,
                UserOrganization.role.in_(
                    [OrganizationRole.owner, OrganizationRole.admin]
                ),
                UserOrganization.is_deleted.is_(False),
            )
        )
        if (other_admin_capable or 0) == 0:
            raise OrganizationWouldHaveNoAdmins(organization_id)


user_organization = UserOrganizationService()
