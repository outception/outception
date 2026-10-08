from outception.auth.routing import DocumentedAuthSubjectAPIRoute
from outception.kit.routing import (
    IncludedInSchemaAPIRoute,
    PaginationAPIRoute,
    SpeakeasyGroupAPIRoute,
    SpeakeasyIgnoreAPIRoute,
    SpeakeasyNameOverrideAPIRoute,
    SpeakeasyPaginationAPIRoute,
    TransactionalAPIRoute,
    get_api_router_class,
)
from outception.kit.versioning import VersionedAPIRoute


class APIRoute(
    VersionedAPIRoute,
    TransactionalAPIRoute,
    IncludedInSchemaAPIRoute,
    DocumentedAuthSubjectAPIRoute,
    PaginationAPIRoute,
    SpeakeasyIgnoreAPIRoute,
    SpeakeasyNameOverrideAPIRoute,
    SpeakeasyGroupAPIRoute,
    SpeakeasyPaginationAPIRoute,
):
    pass


APIRouter = get_api_router_class(APIRoute)

__all__ = ["APIRouter"]
