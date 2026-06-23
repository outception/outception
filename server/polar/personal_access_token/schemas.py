from datetime import datetime, timedelta

from pydantic import UUID4, Field

from polar.auth.scope import Scope
from polar.kit.schemas import Schema, TimestampedSchema


class PersonalAccessToken(TimestampedSchema):
    id: UUID4
    scopes: list[Scope]
    expires_at: datetime | None
    comment: str
    last_used_at: datetime | None


class PersonalAccessTokenCreate(Schema):
    comment: str = Field(min_length=1, max_length=255)
    scopes: list[Scope] = Field(min_length=1)
    expires_in: timedelta | None = Field(
        default=None,
        gt=timedelta(0),
        description="Lifetime of the token; omit for one that never expires.",
    )


class PersonalAccessTokenCreateResponse(Schema):
    personal_access_token: PersonalAccessToken
    token: str
