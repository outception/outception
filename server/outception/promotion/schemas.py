from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, HttpUrl, TypeAdapter

_http_url_adapter = TypeAdapter(HttpUrl)


def _require_http_url(value: str) -> str:
    """Reject non-http(s) URLs (``javascript:``, ``data:``, …) while keeping the
    value a plain string. Promotion links are 302-redirected to and images are
    rendered in ``<img src>``, so both must be http(s)."""
    _http_url_adapter.validate_python(value)
    return value


HttpUrlString = Annotated[str, AfterValidator(_require_http_url)]


# The fixed set of topics a promotion can target. Promotions only ever surface
# in these categories, so buying into any other would silently never render.
# Must stay in sync with ``PROMOTION_TOPICS`` in the clients (web
# ``utils/promotions.ts``, re-exported by mobile).
PROMOTION_CATEGORIES: frozenset[str] = frozenset(
    {
        "news",
        "tech",
        "science",
        "finance",
        "sports",
        "entertainment",
        "gaming",
        "social",
        "world",
    }
)


def _require_known_category(value: str) -> str:
    if value not in PROMOTION_CATEGORIES:
        raise ValueError(f"Unknown promotion category: {value!r}")
    return value


PromotionCategory = Annotated[str, AfterValidator(_require_known_category)]


class PromotionCreate(BaseModel):
    """Request body for buying a promotion. ``blocks`` of featured time are
    purchased; the price and duration are derived server-side."""

    category: PromotionCategory = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=2000)
    link: HttpUrlString | None = Field(default=None, max_length=2048)
    image_url: HttpUrlString | None = Field(default=None, max_length=2048)
    # Each block is PROMOTION_BLOCK_MINUTES of featured time. Capped at 144
    # (a full day at 10 min/block) so a single buy can't monopolise a category.
    blocks: int = Field(default=1, ge=1, le=144)


class PromotionRead(BaseModel):
    """Public view of a promotion (no payment internals)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    author_id: UUID
    category: str
    title: str
    body: str
    link: str | None
    image_url: str | None
    status: str
    duration_minutes: int
    active_until: datetime | None
    created_at: datetime


class PromotionMineRead(PromotionRead):
    """The promoter's own view of a promotion — adds the engagement counters
    (kept off the public ``PromotionRead`` so featured cards don't leak them)."""

    impressions: int
    clicks: int


class PromotionCheckout(BaseModel):
    """The draft promotion's id plus the hosted gateway checkout URL. The
    promotion enters the queue once the order webhook confirms payment."""

    promotion_id: UUID
    url: str


class CategoryPromotions(BaseModel):
    """A category's featured slot plus the in-feed queue behind it."""

    category: str
    active: PromotionRead | None
    queued: list[PromotionRead]


class PromotionPricing(BaseModel):
    """How a promotion is priced — shown on the compose form."""

    block_minutes: int
    price_cents: int
    currency: str = "usd"


class PromotionAnalyticsPeriod(BaseModel):
    """One day's promotion metrics, for the dashboard chart. ``impressions`` and
    ``clicks`` are only populated when sourced from Tinybird (Postgres counters
    aren't time-stamped); they default to 0 otherwise."""

    timestamp: datetime
    spend_cents: int
    promotions: int
    impressions: int = 0
    clicks: int = 0


class PromotionAnalytics(BaseModel):
    """Promotion analytics dashboard: KPI totals plus a daily
    spend series. Scoped to the requesting user's own promotions."""

    total_promotions: int
    total_spend_cents: int
    total_impressions: int
    total_clicks: int
    ctr: float = Field(description="Clicks / impressions, 0 when no impressions.")
    periods: list[PromotionAnalyticsPeriod]


class PromotionPreferences(BaseModel):
    """The authenticated user's promotion-email preference."""

    promotion_emails_enabled: bool
