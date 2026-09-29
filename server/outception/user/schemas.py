import uuid
from datetime import date
from enum import StrEnum
from typing import Annotated, Literal

from fastapi import Depends
from pydantic import UUID4, EmailStr, Field

from outception.auth.scope import Scope
from outception.kit.address import CountryAlpha2Input
from outception.kit.schemas import Schema, TimestampedSchema
from outception.models.user import IdentityVerificationStatus, OAuthPlatform
from outception.organization.schemas import OrganizationWithRole


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
    identity_verified: bool
    identity_verification_status: IdentityVerificationStatus
    first_name: str | None
    last_name: str | None
    country: str | None
    date_of_birth: date | None
    oauth_accounts: list[OAuthAccountRead]
    organizations: list[OrganizationWithRole] = Field(
        default_factory=list,
        description=(
            "Organizations the user is a member of, with their role on each. "
            "Populated by `GET /v1/users/me`; empty otherwise."
        ),
    )


class UserUpdate(Schema):
    first_name: str | None = Field(default=None, max_length=128)
    last_name: str | None = Field(default=None, max_length=128)
    country: CountryAlpha2Input | None = None
    date_of_birth: date | None = None
    accepted_terms_of_service: bool | None = None


class UserScopes(Schema):
    scopes: list[Scope]


###############################################################################
# USER ATTRIBUTION
###############################################################################


class UserSignupAttribution(Schema):
    intent: (
        Literal[
            "creator",
            "purchase",
        ]
        | None
    ) = None

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


class UserDeletionBlockedReason(StrEnum):
    """Reasons why a user account cannot be immediately deleted."""

    HAS_ACTIVE_ORGANIZATIONS = "has_active_organizations"


class BlockingOrganization(Schema):
    """Organization that is blocking user deletion."""

    id: UUID4
    slug: str
    name: str


class UserDeletionResponse(Schema):
    """Response for user deletion request."""

    deleted: bool = Field(
        description="Whether the user account was immediately deleted"
    )
    blocked_reasons: list[UserDeletionBlockedReason] = Field(
        default_factory=list,
        description="Reasons why immediate deletion is blocked",
    )
    blocking_organizations: list[BlockingOrganization] = Field(
        default_factory=list,
        description="Organizations that must be deleted first",
    )
