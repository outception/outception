from fastapi import Depends, Query

from outception.auth.permission import OrganizationPermission
from outception.authz.service import assert_organization_permission
from outception.exceptions import ResourceNotFound
from outception.kit.pagination import ListResource, PaginationParamsQuery
from outception.openapi import APITag
from outception.postgres import (
    AsyncReadSession,
    AsyncSession,
    get_db_read_session,
    get_db_session,
)
from outception.routing import APIRouter

from . import auth, sorting
from .schemas import Organization as OrganizationSchema
from .schemas import OrganizationID, OrganizationUpdate
from .service import organization as organization_service

router = APIRouter(prefix="/organizations", tags=["organizations"])

OrganizationNotFound = {
    "description": "Organization not found.",
    "model": ResourceNotFound.schema(),
}


@router.get("/", response_model=ListResource[OrganizationSchema], tags=[APITag.public])
async def list(
    auth_subject: auth.OrganizationsRead,
    pagination: PaginationParamsQuery,
    sorting: sorting.ListSorting,
    slug: str | None = Query(None, description="Filter by slug."),
    session: AsyncReadSession = Depends(get_db_read_session),
) -> ListResource[OrganizationSchema]:
    """List organizations the authenticated subject can access."""
    results, count = await organization_service.list(
        session, auth_subject, pagination=pagination, sorting=sorting, slug=slug
    )
    return ListResource.from_paginated_results(
        [OrganizationSchema.model_validate(r) for r in results],
        count,
        pagination,
    )


@router.get(
    "/{id}",
    response_model=OrganizationSchema,
    tags=[APITag.public],
    responses={404: OrganizationNotFound},
)
async def get(
    id: OrganizationID,
    auth_subject: auth.OrganizationsRead,
    session: AsyncReadSession = Depends(get_db_read_session),
) -> OrganizationSchema:
    """Get an organization by ID."""
    organization = await organization_service.get(session, auth_subject, id)
    if organization is None:
        raise ResourceNotFound()
    return OrganizationSchema.model_validate(organization)


@router.patch(
    "/{id}",
    response_model=OrganizationSchema,
    tags=[APITag.public],
    responses={404: OrganizationNotFound},
)
async def update(
    id: OrganizationID,
    organization_update: OrganizationUpdate,
    auth_subject: auth.OrganizationsWrite,
    session: AsyncSession = Depends(get_db_session),
) -> OrganizationSchema:
    """Update an organization."""
    organization = await organization_service.get(session, auth_subject, id)
    if organization is None:
        raise ResourceNotFound()
    # Mutating org settings requires the manage permission (owner/admin), not
    # mere membership — mirror the org-access-token endpoints. The fetch above
    # already 404s for non-members, so this 403 can't leak org existence.
    await assert_organization_permission(
        session,
        auth_subject,
        organization.id,
        OrganizationPermission.organization_manage,
    )
    updated = await organization_service.update(
        session, organization, organization_update
    )
    return OrganizationSchema.model_validate(updated)
