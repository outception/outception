from enum import StrEnum
from typing import Any, NotRequired, TypedDict

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from outception.config import settings
from outception.oauth2.schemas import add_oauth2_form_schemas


class OpenAPIExternalDoc(TypedDict):
    description: NotRequired[str]
    url: str


class OpenAPITag(TypedDict):
    name: str
    description: NotRequired[str]
    externalDocs: NotRequired[dict[str, str]]


class APITag(StrEnum):
    """
    Tags used by our documentation to better organize the endpoints.

    They should be set after the "group" tag, which is used to group the endpoints
    in the generated documentation.

    **Example**

        ```py
        router = APIRouter(prefix="/products", tags=["products", APITag.public])
        ```
    """

    public = "public"
    private = "private"

    @classmethod
    def metadata(cls) -> list[OpenAPITag]:
        return [
            {
                "name": cls.public,
                "description": (
                    "Endpoints shown and documented in the Outception API documentation "
                    "and available in our SDKs."
                ),
            },
            {
                "name": cls.private,
                "description": (
                    "Endpoints that should appear in the schema only "
                    "in development to generate our internal JS SDK."
                ),
            },
        ]


class OpenAPIParameters(TypedDict):
    title: str
    summary: str
    description: str
    docs_url: str | None
    redoc_url: str | None
    openapi_url: str | None
    openapi_tags: list[dict[str, Any]]
    servers: list[dict[str, Any]] | None


OPENAPI_PARAMETERS: OpenAPIParameters = {
    "title": "Outception API",
    "summary": "Outception HTTP and Webhooks API",
    "description": "Read the docs at https://outception.com/docs/api-reference/introduction",
    "docs_url": None if settings.is_production() else "/docs",
    "redoc_url": None if settings.is_production() else "/redoc",
    # The docs site renders from a checked-in spec, and the SDK/client
    # generators run against a local server — nothing needs the schema from
    # prod, where the route was unlimited (outside every rate zone) and, until
    # the memoization above, rebuilt the schema on every request.
    "openapi_url": None if settings.is_production() else "/openapi.json",
    "openapi_tags": APITag.metadata(),  # type: ignore
    "servers": [
        {
            "url": "https://api.outception.com",
            "description": "Production environment",
            "x-speakeasy-server-id": "production",
        },
    ],
}


def set_openapi_generator(app: FastAPI) -> None:
    def _openapi_generator() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            openapi_version=app.openapi_version,
            summary=app.summary,
            description=app.description,
            terms_of_service=app.terms_of_service,
            contact=app.contact,
            license_info=app.license_info,
            routes=app.routes,
            webhooks=app.webhooks.routes,
            tags=app.openapi_tags,
            servers=app.servers,
            separate_input_output_schemas=app.separate_input_output_schemas,
        )

        # Memoized: without the assignment the early return above never fires
        # and every /openapi.json request rebuilds the whole schema.
        app.openapi_schema = add_oauth2_form_schemas(openapi_schema)

        return app.openapi_schema

    app.openapi = _openapi_generator  # type: ignore[method-assign]


__all__ = [
    "OPENAPI_PARAMETERS",
    "APITag",
    "set_openapi_generator",
]
