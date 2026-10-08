from enum import StrEnum

from pydantic import GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import core_schema as cs


class Scope(StrEnum):
    openid = "openid"
    profile = "profile"
    email = "email"
    user_read = "user:read"
    user_write = "user:write"

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: cs.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        json_schema = handler(core_schema)
        json_schema = handler.resolve_ref_schema(json_schema)
        json_schema["enumNames"] = SCOPES_SUPPORTED_DISPLAY_NAMES
        return json_schema


READ_ONLY_SCOPES: set[Scope] = {
    Scope.openid,
    Scope.profile,
    Scope.email,
    Scope.user_read,
}

SCOPES_SUPPORTED = [s.value for s in Scope]
SCOPES_SUPPORTED_DISPLAY_NAMES: dict[Scope, str] = {
    Scope.openid: "OpenID",
    Scope.profile: "Read your profile",
    Scope.email: "Read your email address",
    Scope.user_read: "Read your account, followed sources and preferences",
    Scope.user_write: "Manage your account, followed sources and preferences",
}


def scope_to_set(scope: str) -> set[Scope]:
    return {Scope(x) for x in scope.strip().split()}


def scope_to_list(scope: str) -> list[Scope]:
    return list(scope_to_set(scope))
