from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Literal, TypedDict
from urllib.parse import urlparse

from sqlalchemy import (
    TIMESTAMP,
    ColumnElement,
    String,
    UniqueConstraint,
    and_,
)
from sqlalchemy.dialects.postgresql import CITEXT, JSONB
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column

from outception.config import settings
from outception.enums import (
    TaxBehaviorOption,
)
from outception.exceptions import OutceptionError
from outception.kit.currency import PresentmentCurrency
from outception.kit.db.models import RateLimitGroupMixin, RecordModel
from outception.kit.extensions.sqlalchemy import StringEnum

if TYPE_CHECKING:
    from outception.email.sender import EmailFromReply


class OrganizationSocials(TypedDict):
    platform: str
    url: str


class OrganizationDetails(TypedDict, total=False):
    about: str
    product_description: str
    selling_categories: list[str]
    pricing_models: list[str]
    intended_use: str
    customer_acquisition: list[str]
    future_annual_revenue: int
    switching: bool
    switching_from: str | None
    previous_annual_revenue: int


class OrganizationIndividualLegalEntity(TypedDict):
    type: Literal["individual"]


class OrganizationCompanyLegalEntity(TypedDict):
    type: Literal["company"]
    registered_name: str


OrganizationLegalEntity = (
    OrganizationIndividualLegalEntity | OrganizationCompanyLegalEntity
)


class OrganizationStatus(StrEnum):
    CREATED = "created"
    ACTIVE = "active"
    BLOCKED = "blocked"

    def get_display_name(self) -> str:
        return {
            OrganizationStatus.CREATED: "Created",
            OrganizationStatus.ACTIVE: "Active",
            OrganizationStatus.BLOCKED: "Blocked",
        }[self]


class OrganizationCapabilities(TypedDict):
    checkout_payments: bool
    subscription_renewals: bool
    payouts: bool
    refunds: bool
    api_access: bool
    dashboard_access: bool


CapabilityName = Literal[
    "checkout_payments",
    "subscription_renewals",
    "payouts",
    "refunds",
    "api_access",
    "dashboard_access",
]


class InvalidStatusTransitionError(OutceptionError):
    def __init__(
        self, current: "OrganizationStatus", target: "OrganizationStatus"
    ) -> None:
        self.current = current
        self.target = target
        super().__init__(
            f"Cannot transition organization status from "
            f"{current.get_display_name()} to {target.get_display_name()}.",
            400,
        )


STATUS_CAPABILITIES: dict[OrganizationStatus, OrganizationCapabilities] = {
    OrganizationStatus.CREATED: {
        "checkout_payments": False,
        "subscription_renewals": False,
        "payouts": False,
        "refunds": False,
        "api_access": True,
        "dashboard_access": True,
    },
    OrganizationStatus.ACTIVE: {
        "checkout_payments": True,
        "subscription_renewals": True,
        "payouts": True,
        "refunds": True,
        "api_access": True,
        "dashboard_access": True,
    },
    OrganizationStatus.BLOCKED: {
        "checkout_payments": False,
        "subscription_renewals": False,
        "payouts": False,
        "refunds": False,
        "api_access": False,
        "dashboard_access": False,
    },
}


CAPABILITY_METADATA: dict[CapabilityName, tuple[str, str]] = {
    "checkout_payments": (
        "Checkout payments",
        "Allow new checkouts and subscriptions.",
    ),
    "subscription_renewals": (
        "Subscription renewals",
        "Allow recurring billing cycles and dunning retries.",
    ),
    "payouts": (
        "Payouts",
        "Allow funds to be paid out to the payout account.",
    ),
    "refunds": (
        "Refunds",
        "Allow refunds to be issued on this organization's orders.",
    ),
    "api_access": (
        "API access",
        "Allow authenticated API access for team members.",
    ),
    "dashboard_access": (
        "Dashboard access",
        "Allow team members to sign in and access the dashboard.",
    ),
}

CAPABILITY_NAMES: frozenset[str] = frozenset(CAPABILITY_METADATA.keys())


# BLOCKED → ACTIVE additionally requires a reason, enforced at the service layer.
ALLOWED_STATUS_TRANSITIONS: dict[OrganizationStatus, frozenset[OrganizationStatus]] = {
    OrganizationStatus.CREATED: frozenset(
        {OrganizationStatus.ACTIVE, OrganizationStatus.BLOCKED}
    ),
    OrganizationStatus.ACTIVE: frozenset({OrganizationStatus.BLOCKED}),
    OrganizationStatus.BLOCKED: frozenset(
        {OrganizationStatus.CREATED, OrganizationStatus.ACTIVE}
    ),
}


class Organization(RateLimitGroupMixin, RecordModel):
    __tablename__ = "organizations"
    __table_args__ = (UniqueConstraint("slug"),)

    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    slug: Mapped[str] = mapped_column(CITEXT, nullable=False, unique=True)
    slug_history: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    _avatar_url: Mapped[str | None] = mapped_column(
        String, name="avatar_url", nullable=True
    )

    email: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    website: Mapped[str | None] = mapped_column(String, nullable=True, default=None)

    @property
    def avatar_url(self) -> str | None:
        if self._avatar_url:
            return self._avatar_url

        if not self.website or not settings.LOGO_DEV_PUBLISHABLE_KEY:
            return None

        parsed = urlparse(self.website)
        domain = parsed.netloc or parsed.path
        domain = domain.lower().removeprefix("www.")

        return f"https://img.logo.dev/{domain}?size=64&retina=true&token={settings.LOGO_DEV_PUBLISHABLE_KEY}&fallback=404"

    @avatar_url.setter
    def avatar_url(self, value: str | None) -> None:
        self._avatar_url = value

    socials: Mapped[list[OrganizationSocials]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    details: Mapped[OrganizationDetails] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    status: Mapped[OrganizationStatus] = mapped_column(
        StringEnum(OrganizationStatus),
        nullable=False,
        default=OrganizationStatus.CREATED,
    )

    onboarded_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    ai_onboarding_completed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, default=None
    )

    capabilities: Mapped[OrganizationCapabilities] = mapped_column(
        JSONB,
        nullable=False,
        default=lambda: {**STATUS_CAPABILITIES[OrganizationStatus.CREATED]},
    )

    country: Mapped[str | None] = mapped_column(String(2), nullable=True, default=None)

    profile_settings: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    legal_entity: Mapped[OrganizationLegalEntity | None] = mapped_column(
        JSONB, nullable=True, default=None
    )

    #
    # Feature Flags
    #

    feature_settings: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    @property
    def is_member_model_enabled(self) -> bool:
        return self.feature_settings.get("member_model_enabled", False)

    #
    # Currency and tax settings
    #
    default_presentment_currency: Mapped[PresentmentCurrency] = mapped_column(
        String(3), nullable=False, default="usd"
    )
    default_tax_behavior: Mapped[TaxBehaviorOption] = mapped_column(
        StringEnum(TaxBehaviorOption),
        nullable=False,
        default=TaxBehaviorOption.location,
    )

    #
    # Fields synced from GitHub
    #

    # Org description or user bio
    bio: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    company: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    blog: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    location: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    twitter_username: Mapped[str | None] = mapped_column(
        String, nullable=True, default=None
    )

    #
    # End: Fields synced from GitHub
    #

    def _capability(self, name: CapabilityName) -> bool:
        return self.capabilities[name]

    @hybrid_property
    def can_authenticate(self) -> bool:
        return not self.is_deleted and self._capability("api_access")

    @can_authenticate.inplace.expression
    @classmethod
    def _can_authenticate_expression(cls) -> ColumnElement[bool]:
        return and_(
            cls.is_deleted.is_(False),
            cls.capabilities["api_access"].as_boolean().is_(True),
        )

    @hybrid_property
    def can_access_dashboard(self) -> bool:
        return not self.is_deleted and self._capability("dashboard_access")

    @can_access_dashboard.inplace.expression
    @classmethod
    def _can_access_dashboard_expression(cls) -> ColumnElement[bool]:
        return and_(
            cls.is_deleted.is_(False),
            cls.capabilities["dashboard_access"].as_boolean().is_(True),
        )

    @hybrid_property
    def can_accept_payments(self) -> bool:
        return self._capability("checkout_payments")

    @can_accept_payments.inplace.expression
    @classmethod
    def _can_accept_payments_expression(cls) -> ColumnElement[bool]:
        return cls.capabilities["checkout_payments"].as_boolean().is_(True)

    @hybrid_property
    def can_renew_subscriptions(self) -> bool:
        return self._capability("subscription_renewals")

    @can_renew_subscriptions.inplace.expression
    @classmethod
    def _can_renew_subscriptions_expression(cls) -> ColumnElement[bool]:
        return cls.capabilities["subscription_renewals"].as_boolean().is_(True)

    @hybrid_property
    def can_payout(self) -> bool:
        return self._capability("payouts")

    @can_payout.inplace.expression
    @classmethod
    def _can_payout_expression(cls) -> ColumnElement[bool]:
        return cls.capabilities["payouts"].as_boolean().is_(True)

    @hybrid_property
    def can_refund(self) -> bool:
        return self._capability("refunds")

    @can_refund.inplace.expression
    @classmethod
    def _can_refund_expression(cls) -> ColumnElement[bool]:
        return cls.capabilities["refunds"].as_boolean().is_(True)

    def set_status(self, status: OrganizationStatus) -> None:
        if (
            status != self.status
            and status not in ALLOWED_STATUS_TRANSITIONS[self.status]
        ):
            raise InvalidStatusTransitionError(self.status, status)
        self.status = status
        self.capabilities = {**STATUS_CAPABILITIES[status]}

    @property
    def outception_site_url(self) -> str:
        return f"{settings.FRONTEND_BASE_URL}/{self.slug}"

    @property
    def account_url(self) -> str:
        return f"{settings.FRONTEND_BASE_URL}/dashboard/{self.slug}/finance/account"

    def is_blocked(self) -> bool:
        return self.status == OrganizationStatus.BLOCKED

    def is_active(self) -> bool:
        return self.status == OrganizationStatus.ACTIVE

    def statement_descriptor(self, suffix: str = "") -> str:
        max_length = settings.stripe_descriptor_suffix_max_length
        if suffix:
            space_for_slug = max_length - len(suffix)
            return self.slug[:space_for_slug] + suffix
        return self.slug[:max_length]

    @property
    def statement_descriptor_prefixed(self) -> str:
        # Cannot use *. Setting separator to # instead.
        return f"{settings.STRIPE_STATEMENT_DESCRIPTOR}# {self.statement_descriptor()}"

    @property
    def email_from_reply(self) -> "EmailFromReply":
        return {
            "from_name": f"{self.name} (via {settings.EMAIL_FROM_NAME})",
            "from_email_addr": f"{self.slug}@{settings.EMAIL_FROM_DOMAIN}",
            "reply_to_name": self.name,
            "reply_to_email_addr": self.email
            or settings.EMAIL_DEFAULT_REPLY_TO_EMAIL_ADDRESS,
        }
