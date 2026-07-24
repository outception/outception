from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import Select, select

from outception.authz.types import AccessibleOrganizationID
from outception.kit.repository import (
    RepositoryBase,
    RepositorySoftDeletionIDMixin,
    RepositorySoftDeletionMixin,
    RepositorySortingMixin,
    SortingClause,
)
from outception.kit.repository.base import Options
from outception.models import (
    Organization,
    User,
    UserOrganization,
)
from outception.models.organization import (
    OrganizationStatus,
)
from outception.models.user_organization import OrganizationRole

from .sorting import OrganizationSortProperty


class OrganizationRepository(
    RepositorySortingMixin[Organization, OrganizationSortProperty],
    RepositorySoftDeletionIDMixin[Organization, UUID],
    RepositorySoftDeletionMixin[Organization],
    RepositoryBase[Organization],
):
    model = Organization

    async def get_by_id(
        self,
        id: UUID,
        *,
        options: Options = (),
        include_deleted: bool = False,
        include_blocked: bool = False,
        for_update: bool = False,
        nowait: bool = False,
    ) -> Organization | None:
        statement = (
            self.get_base_statement(include_deleted=include_deleted)
            .where(self.model.id == id)
            .options(*options)
        )

        if not include_blocked:
            statement = statement.where(self.model.status != OrganizationStatus.BLOCKED)

        if for_update:
            statement = statement.with_for_update(of=self.model, nowait=nowait)

        return await self.get_one_or_none(statement)

    async def get_all_by_user(self, user: UUID) -> Sequence[Organization]:
        statement = (
            self.get_base_statement()
            .join(UserOrganization)
            .where(
                UserOrganization.user_id == user,
                UserOrganization.is_deleted.is_(False),
                Organization.status != OrganizationStatus.BLOCKED,
            )
        )
        return await self.get_all(statement)

    def get_sorting_clause(self, property: OrganizationSortProperty) -> SortingClause:
        match property:
            case OrganizationSortProperty.created_at:
                return self.model.created_at
            case OrganizationSortProperty.slug:
                return self.model.slug
            case OrganizationSortProperty.organization_name:
                return self.model.name

    def get_statement_by_org_ids(
        self, org_ids: set[AccessibleOrganizationID]
    ) -> Select[tuple[Organization]]:
        return self.get_base_statement().where(
            Organization.id.in_(org_ids),
            Organization.status != OrganizationStatus.BLOCKED,
        )

    async def get_owner_user(self, organization: Organization) -> User | None:
        """Get the owner of the organization."""
        statement = (
            select(User)
            .join(UserOrganization, UserOrganization.user_id == User.id)
            .where(
                UserOrganization.organization_id == organization.id,
                UserOrganization.role == OrganizationRole.owner,
                UserOrganization.is_deleted.is_(False),
                User.is_deleted.is_(False),
            )
        )
        result = await self.session.execute(statement)
        return result.unique().scalar_one_or_none()
