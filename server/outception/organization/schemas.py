import re
from enum import StrEnum
from typing import Annotated, Any, Literal
from urllib.parse import urlparse

from pydantic import (
    UUID4,
    AfterValidator,
    BeforeValidator,
    Field,
    StringConstraints,
    computed_field,
    model_validator,
)
from pydantic.json_schema import SkipJsonSchema
from pydantic.networks import HttpUrl

from outception.auth.permission import OrganizationPermission
from outception.config import settings
from outception.enums import TaxBehaviorOption
from outception.kit.address import CountryAlpha2, CountryAlpha2Input
from outception.kit.currency import PresentmentCurrency
from outception.kit.email import EmailStrDNS
from outception.kit.schemas import (
    ORGANIZATION_ID_EXAMPLE,
    HttpUrlToStr,
    IDSchema,
    MergeJSONSchema,
    Schema,
    SelectorWidget,
    SlugValidator,
    TimestampedSchema,
)
from outception.models.organization import (
    OrganizationStatus,
)
from outception.models.user_organization import (
    OrganizationNotificationSettings,
    OrganizationRole,
)

OrganizationID = Annotated[
    UUID4,
    MergeJSONSchema({"description": "The organization ID."}),
    SelectorWidget("/v1/organizations", "Organization", "name"),
    Field(examples=[ORGANIZATION_ID_EXAMPLE]),
]


def validate_blocked_words(value: str) -> str:
    pattern = re.compile(
        r"\b("
        + "|".join(re.escape(w) for w in settings.ORGANIZATION_BLOCKED_WORDS)
        + r")\b",
        re.IGNORECASE,
    )
    if pattern.search(value):
        raise ValueError("This name is not allowed.")
    return value


NameInput = Annotated[
    str,
    StringConstraints(min_length=3),
    AfterValidator(validate_blocked_words),
]


def validate_reserved_keywords(value: str) -> str:
    if value in settings.ORGANIZATION_SLUG_RESERVED_KEYWORDS:
        raise ValueError("This slug is reserved.")
    return value


SLUG_MAX_LENGTH = 64


SlugInput = Annotated[
    str,
    StringConstraints(to_lower=True, min_length=3, max_length=SLUG_MAX_LENGTH),
    SlugValidator,
    AfterValidator(validate_reserved_keywords),
    AfterValidator(validate_blocked_words),
]


class OrganizationSlugCheck(Schema):
    slug: str = Field(description="The slug to check availability for.")


class OrganizationSlugAvailability(Schema):
    available: bool = Field(
        description="Whether the slug is available for a new organization."
    )


def _discard_logo_dev_url(url: HttpUrl) -> HttpUrl | None:
    if url.host and url.host.endswith("logo.dev"):
        return None
    return url


AvatarUrl = Annotated[HttpUrlToStr, AfterValidator(_discard_logo_dev_url)]


class OrganizationCapabilities(Schema):
    api_access: bool = Field(description="Whether the organization can access the API.")
    dashboard_access: bool = Field(
        description="Whether the organization can access the dashboard."
    )


class OrganizationDetails(Schema):
    about: str | None = Field(
        None,
        deprecated=True,
        description="Brief information about you and your business.",
    )
    product_description: str | None = Field(
        None, description="Description of digital products being sold."
    )
    selling_categories: list[str] = Field(
        default_factory=list, description="Categories of products being sold."
    )
    pricing_models: list[str] = Field(
        default_factory=list, description="Pricing models used by the organization."
    )
    intended_use: str | None = Field(
        None,
        deprecated=True,
        description="How the organization will integrate and use Outception.",
    )
    customer_acquisition: list[str] = Field(
        default_factory=list,
        deprecated=True,
        description="Main customer acquisition channels.",
    )
    future_annual_revenue: int | None = Field(
        None,
        ge=0,
        deprecated=True,
        description="Estimated revenue in the next 12 months",
    )
    switching: bool = Field(False, description="Switching from another platform?")
    switching_from: (
        Literal["paddle", "lemon_squeezy", "gumroad", "stripe", "other"] | None
    ) = Field(None, description="Which platform the organization is migrating from.")
    previous_annual_revenue: int | None = Field(
        None,
        ge=0,
        deprecated=True,
        description="Revenue from last year if applicable.",
    )


class OrganizationSocialPlatforms(StrEnum):
    x = "x"
    github = "github"
    facebook = "facebook"
    instagram = "instagram"
    youtube = "youtube"
    tiktok = "tiktok"
    linkedin = "linkedin"
    threads = "threads"
    discord = "discord"
    other = "other"


PLATFORM_DOMAINS = {
    "x": ["twitter.com", "x.com"],
    "github": ["github.com"],
    "facebook": ["facebook.com", "fb.com"],
    "instagram": ["instagram.com"],
    "youtube": ["youtube.com", "youtu.be"],
    "tiktok": ["tiktok.com"],
    "linkedin": ["linkedin.com"],
    "threads": ["threads.net"],
    "discord": ["discord.gg", "discord.com"],
}

# Reverse mapping: domain -> platform for auto-detection
DOMAIN_TO_PLATFORM: dict[str, str] = {}
for _platform, _domains in PLATFORM_DOMAINS.items():
    for _domain in _domains:
        DOMAIN_TO_PLATFORM[_domain] = _platform


def detect_platform_from_url(url: str) -> str | None:
    """Detect the social platform from a URL's hostname."""
    try:
        parsed = urlparse(url.lower())
        hostname = parsed.hostname or ""
        # Strip www. prefix
        if hostname.startswith("www."):
            hostname = hostname[4:]
        return DOMAIN_TO_PLATFORM.get(hostname)
    except Exception:
        return None


class OrganizationSocialLink(Schema):
    platform: OrganizationSocialPlatforms = Field(
        ..., description="The social platform of the URL"
    )
    url: HttpUrlToStr = Field(..., description="The URL to the organization profile")

    @model_validator(mode="before")
    @classmethod
    def validate_url(cls, data: dict[str, Any]) -> dict[str, Any]:
        url = data.get("url", "").lower()
        if not url:
            return data

        # Auto-detect platform from URL domain, fallback to "other"
        detected = detect_platform_from_url(url)
        data["platform"] = detected or "other"

        return data


class OrganizationBase(IDSchema, TimestampedSchema):
    name: str = Field(
        description="Organization name shown in promotions, emails, etc.",
    )
    slug: str = Field(
        description="Unique organization slug used in promotions and credit card statements.",
    )
    avatar_url: str | None = Field(
        description="Avatar URL shown in promotions, emails, etc."
    )
    # Deprecated attributes
    bio: SkipJsonSchema[str | None] = Field(..., deprecated="")
    company: SkipJsonSchema[str | None] = Field(
        ...,
        deprecated="Legacy attribute no longer in use.",
    )
    blog: SkipJsonSchema[str | None] = Field(
        ...,
        deprecated="Legacy attribute no longer in use. See `socials` instead.",
    )
    location: SkipJsonSchema[str | None] = Field(
        ...,
        deprecated="Legacy attribute no longer in use.",
    )
    twitter_username: SkipJsonSchema[str | None] = Field(
        ...,
        deprecated="Legacy attribute no longer in use. See `socials` instead.",
    )

    pledge_minimum_amount: SkipJsonSchema[int] = Field(0, deprecated=True)
    pledge_badge_show_amount: SkipJsonSchema[bool] = Field(False, deprecated=True)
    default_upfront_split_to_contributors: SkipJsonSchema[int | None] = Field(
        None, deprecated=True
    )


class LegacyOrganizationStatus(StrEnum):
    """
    Legacy organization status values kept for backward compatibility in schemas
    using OrganizationPublicBase.
    """

    CREATED = "created"
    UNDER_REVIEW = "under_review"
    DENIED = "denied"
    ACTIVE = "active"

    @classmethod
    def from_status(cls, status: OrganizationStatus) -> "LegacyOrganizationStatus":
        mapping = {
            OrganizationStatus.CREATED: LegacyOrganizationStatus.CREATED,
            OrganizationStatus.ACTIVE: LegacyOrganizationStatus.ACTIVE,
            OrganizationStatus.BLOCKED: LegacyOrganizationStatus.DENIED,
        }
        try:
            return mapping[status]
        except KeyError as e:
            raise ValueError("Unknown OrganizationStatus") from e


class OrganizationPublicBase(OrganizationBase):
    # Attributes that we used to have publicly, but now want to hide from
    # the public schema.
    # Keep it for now for backward compatibility in the SDK
    email: SkipJsonSchema[str | None]
    website: SkipJsonSchema[str | None]
    socials: SkipJsonSchema[list[OrganizationSocialLink]]
    status: Annotated[
        SkipJsonSchema[LegacyOrganizationStatus],
        BeforeValidator(LegacyOrganizationStatus.from_status),
    ]


class Organization(OrganizationBase):
    email: str | None = Field(description="Public support email.")
    website: str | None = Field(description="Official website of the organization.")
    socials: list[OrganizationSocialLink] = Field(
        description="Links to social profiles.",
    )
    status: OrganizationStatus = Field(description="Current organization status")

    default_presentment_currency: str = Field(
        description=(
            "Default presentment currency. "
            "Used as a fallback, "
            "if the customer's local currency is not available."
        )
    )
    default_tax_behavior: TaxBehaviorOption = Field(
        description="Default tax behavior applied on promotions."
    )
    country: CountryAlpha2 | None = Field(
        None, description="Two-letter country code (ISO 3166-1 alpha-2)."
    )

    capabilities: OrganizationCapabilities = Field(
        description="Capabilities currently granted to the organization.",
    )

    @computed_field(  # type: ignore[prop-decorator]
        deprecated="Notification preferences are now configured per member."
    )
    @property
    def notification_settings(self) -> SkipJsonSchema[OrganizationNotificationSettings]:
        """Deprecated. Notification preferences are now configured per member,
        not at the organization level. Still serialized with a static default for
        backward compatibility with older SDK versions that require the field, but
        hidden from the schema so it's dropped from future SDK versions."""
        return OrganizationNotificationSettings(
            new_order=True, new_subscription=True, chargeback_prevention=True
        )


class OrganizationWithRole(Organization):
    """Variant of `Organization` embedded on `GET /v1/users/me` that
    includes the user's role on the organization."""

    role: OrganizationRole = Field(description="The user's role on this organization.")

    @classmethod
    def from_organization(
        cls, organization: Any, role: OrganizationRole
    ) -> "OrganizationWithRole":
        """Build from a SQLAlchemy `Organization` plus the user's role."""
        return cls.model_validate(
            {**Organization.model_validate(organization).model_dump(), "role": role}
        )


class OrganizationRoleDefinition(Schema):
    """A role available in an organization and the permissions it grants."""

    id: OrganizationRole = Field(description="The role identifier.")
    permissions: list[OrganizationPermission] = Field(
        description="The permissions this role grants in the organization."
    )


class OrganizationKYC(Organization):
    """Organization with compliance/KYC details. Only returned from the dedicated KYC endpoint."""

    details: OrganizationDetails | None = Field(
        None,
        description="Organization compliance details. Only visible to organization members.",
    )


class OrganizationIndividualLegalEntitySchema(Schema):
    type: Literal["individual"]


class OrganizationCompanyLegalEntitySchema(Schema):
    type: Literal["company"]
    registered_name: str


OrganizationLegalEntitySchema = Annotated[
    OrganizationIndividualLegalEntitySchema | OrganizationCompanyLegalEntitySchema,
    Field(discriminator="type"),
]


class OrganizationCreate(Schema):
    name: NameInput
    slug: SlugInput
    avatar_url: AvatarUrl | None = None
    legal_entity: OrganizationLegalEntitySchema | None = None
    email: EmailStrDNS | None = Field(None, description="Public support email.")
    website: HttpUrlToStr | None = Field(
        None, description="Official website of the organization."
    )
    socials: list[OrganizationSocialLink] | None = Field(
        None,
        description="Link to social profiles.",
    )
    details: OrganizationDetails | None = Field(
        None,
        description="Additional, private, business details Outception needs about active organizations for compliance (KYC).",
    )
    country: CountryAlpha2Input | None = Field(
        None, description="Two-letter country code (ISO 3166-1 alpha-2)."
    )
    default_presentment_currency: PresentmentCurrency = Field(
        PresentmentCurrency.usd,
        description="Default presentment currency for the organization",
    )
    default_tax_behavior: TaxBehaviorOption = Field(
        default=TaxBehaviorOption.location,
        description="Default tax behavior applied on promotions.",
    )


class OrganizationUpdate(Schema):
    name: NameInput | None = None
    avatar_url: AvatarUrl | None = None

    email: EmailStrDNS | None = Field(None, description="Public support email.")
    website: HttpUrlToStr | None = Field(
        None, description="Official website of the organization."
    )
    socials: list[OrganizationSocialLink] | None = Field(
        None, description="Links to social profiles."
    )
    details: OrganizationDetails | None = Field(
        None,
        description="Additional, private, business details Outception needs about active organizations for compliance (KYC).",
    )
    country: CountryAlpha2Input | None = Field(
        None, description="Two-letter country code (ISO 3166-1 alpha-2)."
    )

    default_presentment_currency: PresentmentCurrency | None = Field(
        None, description="Default presentment currency for the organization"
    )
    default_tax_behavior: TaxBehaviorOption | None = Field(
        None, description="Default tax behavior applied on promotions."
    )
