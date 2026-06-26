from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, func, select, update

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
    OrganizationCapabilities,
    OrganizationStatus,
    SnoozeType,
)
from outception.models.user_organization import OrganizationRole

from .sorting import OrganizationSortProperty

# Maximum orgs the unsnooze cron processes per run. Bounds worst-case
# transaction size when many time-based snoozes expire in the same window.
UNSNOOZE_EXPIRED_BATCH_SIZE = 500


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
    ) -> Organization | None:
        statement = (
            self.get_base_statement(include_deleted=include_deleted)
            .where(self.model.id == id)
            .options(*options)
        )

        if not include_blocked:
            statement = statement.where(self.model.status != OrganizationStatus.BLOCKED)

        return await self.get_one_or_none(statement)

    async def get_by_slug(
        self, slug: str, include_deleted: bool = False
    ) -> Organization | None:
        statement = self.get_base_statement(include_deleted=include_deleted).where(
            Organization.slug == slug
        )
        return await self.get_one_or_none(statement)

    async def slug_exists(self, slug: str) -> bool:
        """Check if slug exists, including soft-deleted organizations.

        Soft-deleted organizations are included to prevent slug reuse,
        ensuring backoffice links continue to work.
        """
        statement = self.get_base_statement(include_deleted=True).where(
            Organization.slug == slug
        )
        result = await self.get_one_or_none(statement)
        return result is not None

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

    async def get_expired_time_based_snoozes(
        self, now: datetime, *, limit: int = UNSNOOZE_EXPIRED_BATCH_SIZE
    ) -> Sequence[Organization]:
        """Snoozed orgs whose TIME_BASED deadline has passed."""
        statement = (
            self.get_base_statement()
            .where(
                Organization.status == OrganizationStatus.SNOOZED,
                Organization.snooze_type == SnoozeType.TIME_BASED,
                Organization.snoozed_until.is_not(None),
                Organization.snoozed_until <= now,
            )
            .order_by(Organization.snoozed_until.asc())
            .limit(limit)
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
            case OrganizationSortProperty.next_review_threshold:
                return self.model.next_review_threshold
            case OrganizationSortProperty.days_in_status:
                # Calculate days since status was last updated
                return (
                    func.extract(
                        "epoch",
                        func.now()
                        - func.coalesce(
                            self.model.status_updated_at, self.model.modified_at
                        ),
                    )
                    / 86400
                )

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

    async def confirm_review_atomic(
        self,
        organization_id: UUID,
        *,
        next_review_threshold: int | None,
        min_threshold: int,
        active_capabilities: OrganizationCapabilities,
        now: datetime,
    ) -> Organization | None:
        """Atomically transition a REVIEW or SNOOZED organization to ACTIVE.

        Returns the updated ``Organization`` (also merged into the session's
        identity map via ``populate_existing``), or ``None`` if the row was
        no longer in a confirmable state — typically because another worker
        already won the race and flipped the org back to ACTIVE.

        When ``next_review_threshold`` is ``None``, the threshold is doubled
        server-side from the current row (floored at ``min_threshold``) so
        that N concurrent confirms doubling at once cannot collapse onto a
        shared stale snapshot.
        """
        threshold_expr = (
            func.greatest(Organization.next_review_threshold * 2, min_threshold)
            if next_review_threshold is None
            else next_review_threshold
        )

        stmt = (
            update(Organization)
            .where(
                Organization.id == organization_id,
                Organization.status.in_(
                    [OrganizationStatus.REVIEW, OrganizationStatus.SNOOZED]
                ),
            )
            .values(
                status=OrganizationStatus.ACTIVE,
                status_updated_at=now,
                capabilities=active_capabilities,
                next_review_threshold=threshold_expr,
                initially_reviewed_at=func.coalesce(
                    Organization.initially_reviewed_at, now
                ),
            )
            .returning(Organization)
            .execution_options(populate_existing=True)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def increment_customer_invoice_next_number(
        self, organization_id: UUID
    ) -> int:
        """
        Atomically increment customer_invoice_next_number and return the value
        before increment.
        """
        stmt = (
            update(Organization)
            .where(Organization.id == organization_id)
            .values(
                customer_invoice_next_number=Organization.customer_invoice_next_number
                + 1
            )
            .returning(Organization.customer_invoice_next_number)
        )
        result = await self.session.execute(stmt)
        next_number = result.scalar_one()
        return next_number - 1

    async def get_all_by_owner_user(self, user_id: UUID) -> Sequence[Organization]:
        statement = (
            self.get_base_statement()
            .join(
                UserOrganization,
                UserOrganization.organization_id == Organization.id,
            )
            .where(
                UserOrganization.user_id == user_id,
                UserOrganization.role == OrganizationRole.owner,
                UserOrganization.is_deleted.is_(False),
            )
        )
        return await self.get_all(statement)
