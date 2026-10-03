from collections.abc import Sequence
from enum import StrEnum
from typing import TYPE_CHECKING, Any, NotRequired, TypedDict

from fastapi.openapi.utils import get_openapi as _get_openapi
from fastapi.routing import RouteContext
from starlette.routing import BaseRoute

from outception.kit.metadata import add_metadata_query_schema
from outception.kit.versioning import api_version_context, prune_version_omitted_schemas
from outception.oauth2.schemas import add_oauth2_form_schemas

if TYPE_CHECKING:
    from outception.kit.versioning import APIVersion


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
    mcp = "mcp"
    cli = "cli"

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
            {
                "name": cls.mcp,
                "description": "Endpoints supported by Outception's MCP server.",
            },
            {
                "name": cls.cli,
                "description": "Endpoints exposed as commands by Outception's CLI.",
            },
        ]


def cli_preview(*fields: tuple[str, str]) -> dict[str, Any]:
    return {
        "x-outception-cli-preview": {
            "fields": [{"key": key, "label": label} for key, label in fields]
        }
    }


type CLIConfirmValue = str | bool | int | float | None


def cli_confirm() -> dict[str, Any]:
    return {"x-outception-cli-confirm": True}


def cli_confirm_equals(value: CLIConfirmValue) -> dict[str, Any]:
    return {"x-outception-cli-confirm": {"equals": value}}


def cli_confirm_one_of(*values: CLIConfirmValue) -> dict[str, Any]:
    return {"x-outception-cli-confirm": {"one_of": list(values)}}


def get_openapi(
    version: "APIVersion",
    route_contexts: Sequence[RouteContext],
    webhooks: Sequence[BaseRoute],
) -> dict[str, Any]:
    with api_version_context(version):
        openapi_schema = _get_openapi(
            title="Outception API",
            version=str(version),
            summary="Outception HTTP and Webhooks API",
            description="Read the docs at https://outception.sh/docs/api-reference",
            routes=route_contexts,
            webhooks=webhooks,
            tags=APITag.metadata(),  # type: ignore
            servers=[
                {
                    "url": "https://api.outception.sh",
                    "description": "Production environment",
                    "x-speakeasy-server-id": "production",
                    "x-outception-environment": "production",
                },
                {
                    "url": "https://sandbox-api.outception.sh",
                    "description": "Sandbox environment",
                    "x-speakeasy-server-id": "sandbox",
                    "x-outception-environment": "sandbox",
                },
            ],
        )
    openapi_schema = add_metadata_query_schema(openapi_schema)
    openapi_schema = add_oauth2_form_schemas(openapi_schema)
    openapi_schema = prune_version_omitted_schemas(openapi_schema, version)

    return openapi_schema


__all__ = [
    "APITag",
    "get_openapi",
]
