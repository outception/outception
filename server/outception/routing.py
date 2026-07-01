from outception.auth.routing import DocumentedAuthSubjectAPIRoute
from outception.kit.routing import (
    AutoCommitAPIRoute,
    IncludedInSchemaAPIRoute,
    SpeakeasyGroupAPIRoute,
    SpeakeasyIgnoreAPIRoute,
    SpeakeasyNameOverrideAPIRoute,
    SpeakeasyPaginationAPIRoute,
    get_api_router_class,
)


class APIRoute(
    AutoCommitAPIRoute,
    IncludedInSchemaAPIRoute,
    DocumentedAuthSubjectAPIRoute,
    SpeakeasyIgnoreAPIRoute,
    SpeakeasyNameOverrideAPIRoute,
    SpeakeasyGroupAPIRoute,
    SpeakeasyPaginationAPIRoute,
):
    pass


APIRouter = get_api_router_class(APIRoute)

__all__ = ["APIRouter"]
