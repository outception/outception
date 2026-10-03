import uuid
from datetime import date
from typing import Annotated

from fastapi import Depends
from pydantic import EmailStr, Field

from outception.auth.scope import Scope
from outception.kit.address import CountryAlpha2Input
from outception.kit.schemas import Schema, TimestampedSchema
from outception.models.user import OAuthPlatform


class UserBase(Schema):
    email: EmailStr
    avatar_url: str | None


class OAuthAccountRead(TimestampedSchema):
    platform: OAuthPlatform
    account_id: str
    account_email: str
    account_username: str | None


class UserRead(UserBase, TimestampedSchema):
    id: uuid.UUID
    accepted_terms_of_service: bool
    is_admin: bool
    first_name: str | None
    last_name: str | None
    country: str | None
    date_of_birth: date | None
    oauth_accounts: list[OAuthAccountRead]


class UserUpdate(Schema):
    first_name: str | None = None
    last_name: str | None = None
    country: CountryAlpha2Input | None = None
    date_of_birth: date | None = None
    accepted_terms_of_service: bool | None = None


class UserScopes(Schema):
    scopes: list[Scope]


###############################################################################
# USER ATTRIBUTION
###############################################################################


class UserSignupAttribution(Schema):
    # Website source
    path: str | None = None
    host: str | None = None

    # UTM parameters
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None

    campaign: str | None = None


UserSignupAttributionQueryJSON = str | None


async def get_signup_attribution(
    attribution: UserSignupAttributionQueryJSON = None,
) -> UserSignupAttribution | None:
    if attribution:
        return UserSignupAttribution.model_validate_json(attribution)
    return None


UserSignupAttributionQuery = Annotated[
    UserSignupAttribution | None, Depends(get_signup_attribution)
]


class UserDeletionResponse(Schema):
    """Response for user deletion request."""

    deleted: bool = Field(
        description="Whether the user account was immediately deleted"
    )
