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

    organizations_read = "organizations:read"
    organizations_write = "organizations:write"

    members_read = "members:read"
    members_write = "members:write"

    notifications_read = "notifications:read"
    notifications_write = "notifications:write"

    notification_recipients_read = "notification_recipients:read"
    notification_recipients_write = "notification_recipients:write"

    organization_access_tokens_read = "organization_access_tokens:read"
    organization_access_tokens_write = "organization_access_tokens:write"

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
    Scope.organizations_read,
    Scope.members_read,
    Scope.notifications_read,
    Scope.notification_recipients_read,
    Scope.organization_access_tokens_read,
}

SCOPES_SUPPORTED = [s.value for s in Scope]
SCOPES_SUPPORTED_DISPLAY_NAMES: dict[Scope, str] = {
    Scope.openid: "OpenID",
    Scope.profile: "Read your profile",
    Scope.email: "Read your email address",
    Scope.user_read: "Read your user account",
    Scope.user_write: "Manage your user account",
    Scope.organizations_read: "Read your organizations",
    Scope.organizations_write: "Create or modify organizations",
    Scope.members_read: "Read members",
    Scope.members_write: "Create or modify members",
    Scope.notifications_read: "Read notifications",
    Scope.notifications_write: "Mark notifications as read",
    Scope.notification_recipients_read: "Read notification recipients",
    Scope.notification_recipients_write: "Create or modify notification recipients",
    Scope.organization_access_tokens_read: "Read organization access tokens",
    Scope.organization_access_tokens_write: "Create or modify organization access tokens",
}


def scope_to_set(scope: str) -> set[Scope]:
    return {Scope(x) for x in scope.strip().split()}


def scope_to_list(scope: str) -> list[Scope]:
    return list(scope_to_set(scope))
