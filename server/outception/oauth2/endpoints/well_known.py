from typing import Any

from fastapi import Depends, Request
from fastapi.responses import PlainTextResponse

from outception.config import settings
from outception.exceptions import ResourceNotFound
from outception.routing import APIRouter

from ..authorization_server import AuthorizationServer
from ..dependencies import get_authorization_server
from ..metadata import get_server_metadata

router = APIRouter(prefix="/.well-known", tags=["well_known"], include_in_schema=False)


@router.get("/jwks.json", name="well_known.jwks")
async def well_known_jwks() -> dict[str, Any]:
    return settings.JWKS.as_dict(is_private=False)


@router.get(
    "/apple-developer-domain-association.txt",
    name="well_known.apple_domain_association",
    response_class=PlainTextResponse,
)
async def apple_domain_association() -> str:
    """Serve the "Sign in with Apple" domain-verification token so Apple can
    confirm we own this domain. The token is public (operator config); a 404
    until it's set means Apple verification simply isn't configured yet."""
    if not settings.APPLE_DOMAIN_ASSOCIATION:
        raise ResourceNotFound()
    return settings.APPLE_DOMAIN_ASSOCIATION


@router.get("/openid-configuration", name="well_known.openid_configuration")
async def well_known_openid_configuration(
    request: Request,
    authorization_server: AuthorizationServer = Depends(get_authorization_server),
) -> dict[str, Any]:
    def _url_for(name: str) -> str:
        return str(request.url_for(name))

    metadata = get_server_metadata(authorization_server, _url_for)
    return metadata.model_dump(exclude_unset=True)
