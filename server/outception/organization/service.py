import uuid
from collections.abc import Sequence

from outception.auth.models import AuthSubject, Organization, User
from outception.authz.service import get_accessible_org_ids
from outception.kit.pagination import PaginationParams
from outception.kit.repository.base import Options
from outception.kit.sorting import Sorting
from outception.models import Organization as OrganizationModel
from outception.postgres import AsyncReadSession, AsyncSession

from .repository import OrganizationRepository
from .schemas import OrganizationUpdate
from .sorting import OrganizationSortProperty


class OrganizationService:
    """Core organization service.

    The Merchant-of-Record surface (accounts, payouts, products, customers,
    reviews, billing) was removed with the MoR teardown. This keeps the
    membership/identity operations the dashboard and auth flows need.
    """

    async def list(
        self,
        session: AsyncReadSession,
        auth_subject: AuthSubject[User | Organization],
        *,
        pagination: PaginationParams,
        sorting: list[Sorting[OrganizationSortProperty]],
        slug: str | None = None,
    ) -> tuple[Sequence[OrganizationModel], int]:
        repository = OrganizationRepository.from_session(session)
        org_ids = await get_accessible_org_ids(session, auth_subject)
        statement = repository.get_statement_by_org_ids(org_ids)
        if slug is not None:
            statement = statement.where(OrganizationModel.slug == slug)
        statement = repository.apply_sorting(statement, sorting)
        return await repository.paginate(
            statement, limit=pagination.limit, page=pagination.page
        )

    async def get(
        self,
        session: AsyncReadSession,
        auth_subject: AuthSubject[User | Organization],
        id: uuid.UUID,
        *,
        options: Options = (),
    ) -> OrganizationModel | None:
        repository = OrganizationRepository.from_session(session)
        org_ids = await get_accessible_org_ids(session, auth_subject)
        statement = (
            repository.get_statement_by_org_ids(org_ids)
            .where(OrganizationModel.id == id)
            .options(*options)
        )
        return await repository.get_one_or_none(statement)

    async def update(
        self,
        session: AsyncSession,
        organization: OrganizationModel,
        organization_update: OrganizationUpdate,
    ) -> OrganizationModel:
        repository = OrganizationRepository.from_session(session)
        update_dict = organization_update.model_dump(exclude_unset=True)
        return await repository.update(organization, update_dict=update_dict)


organization = OrganizationService()
