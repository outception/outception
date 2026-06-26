from datetime import datetime, timedelta
from enum import StrEnum

from pydantic import UUID4, Field

from outception.auth.scope import SCOPES_SUPPORTED, Scope
from outception.kit.schemas import Schema, TimestampedSchema
from outception.organization.schemas import OrganizationID

AvailableScope = StrEnum(  # type: ignore
    "AvailableScope",
    {Scope(v).name: v for v in SCOPES_SUPPORTED},
)


class OrganizationAccessTokenCreate(Schema):
    organization_id: UUID4 | None = None
    comment: str
    expires_in: timedelta | None = Field(default=None, gt=timedelta(0))
    scopes: list[AvailableScope] = Field(min_length=1)  # pyright: ignore


class OrganizationAccessTokenUpdate(Schema):
    comment: str | None = None
    scopes: list[AvailableScope] | None = None  # pyright: ignore


class OrganizationAccessToken(TimestampedSchema):
    id: UUID4
    scopes: list[Scope]
    expires_at: datetime | None
    comment: str
    last_used_at: datetime | None
    organization_id: OrganizationID


class OrganizationAccessTokenCreateResponse(Schema):
    organization_access_token: OrganizationAccessToken
    token: str
