import hashlib
from datetime import timedelta
from uuid import UUID

from fastapi import Depends, Query, Request
from fastapi.responses import RedirectResponse

from polar.billing.service import billing as billing_service
from polar.config import settings
from polar.kit.utils import utc_now
from polar.openapi import APITag
from polar.postgres import (
    AsyncReadSession,
    AsyncSession,
    get_db_read_session,
    get_db_session,
)
from polar.redis import Redis, get_redis
from polar.routing import APIRouter

from . import auth
from .exceptions import PromotionUnavailable
from .schemas import (
    CategoryPromotions,
    PromotionAnalytics,
    PromotionAnalyticsPeriod,
    PromotionCheckout,
    PromotionCreate,
    PromotionMineRead,
    PromotionPreferences,
    PromotionPricing,
    PromotionRead,
)
from .service import BLOCK_MINUTES, PRICE_CENTS_PER_BLOCK
from .service import promotion as promotion_service

router = APIRouter(prefix="/promotions", tags=["promotions"])


def _viewer_key(request: Request) -> str:
    """A stable, privacy-preserving identifier for the requesting viewer, used
    to dedupe impressions. Derived from the (proxy-aware) client IP and
    user-agent, then hashed so no raw IP is stored."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    else:
        ip = request.headers.get("x-real-ip") or (
            request.client.host if request.client else "unknown"
        )
    user_agent = request.headers.get("user-agent", "")
    return hashlib.sha256(f"{ip}|{user_agent}".encode()).hexdigest()[:32]


@router.get("/pricing", response_model=PromotionPricing, tags=[APITag.public])
async def get_pricing() -> PromotionPricing:
    """Featured-slot pricing for the compose form."""
    return PromotionPricing(
        block_minutes=BLOCK_MINUTES, price_cents=PRICE_CENTS_PER_BLOCK
    )


@router.get("/featured", response_model=list[PromotionRead], tags=[APITag.public])
async def get_featured(
    request: Request,
    categories: str = Query(
        ..., description="Comma-separated category ids the reader cares about."
    ),
    session: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> list[PromotionRead]:
    """The active "in focus" promotion for each requested category (at most one
    per category). Advances each category's queue as a side effect. Impressions
    are deduped per viewer so background polling doesn't inflate the count."""
    cats = [c.strip() for c in categories.split(",") if c.strip()]
    if not cats:
        return []
    promotions = await promotion_service.get_featured(
        session, cats, redis=redis, viewer_key=_viewer_key(request)
    )
    return [PromotionRead.model_validate(p) for p in promotions]


@router.get(
    "/category/{category}",
    response_model=CategoryPromotions,
    tags=[APITag.public],
)
async def get_category(
    category: str,
    session: AsyncSession = Depends(get_db_session),
) -> CategoryPromotions:
    """A category's featured promotion plus the queued promotions behind it
    (shown as in-feed "Promoted" cards until their turn)."""
    active, queued = await promotion_service.get_category(session, category)
    return CategoryPromotions(
        category=category,
        active=PromotionRead.model_validate(active) if active else None,
        queued=[PromotionRead.model_validate(p) for p in queued],
    )


@router.get("/mine", response_model=list[PromotionMineRead], tags=[APITag.private])
async def list_mine(
    auth_subject: auth.PromotionUser,
    session: AsyncReadSession = Depends(get_db_read_session),
) -> list[PromotionMineRead]:
    """The authenticated user's promotions, newest first."""
    promotions = await promotion_service.list_mine(session, auth_subject.subject.id)
    return [PromotionMineRead.model_validate(p) for p in promotions]


@router.get(
    "/preferences", response_model=PromotionPreferences, tags=[APITag.private]
)
async def get_preferences(
    auth_subject: auth.PromotionUser,
) -> PromotionPreferences:
    """Whether the authenticated user receives promotion lifecycle emails."""
    return PromotionPreferences(
        promotion_emails_enabled=auth_subject.subject.promotion_emails_enabled
    )


@router.patch(
    "/preferences", response_model=PromotionPreferences, tags=[APITag.private]
)
async def update_preferences(
    data: PromotionPreferences,
    auth_subject: auth.PromotionUserWrite,
    session: AsyncSession = Depends(get_db_session),
) -> PromotionPreferences:
    """Turn the promotion lifecycle emails (go-live / queued / expiry) on or off.

    Accepts web sessions and API tokens, so both the web dashboard and the
    mobile app can set it."""
    user = auth_subject.subject
    user.promotion_emails_enabled = data.promotion_emails_enabled
    session.add(user)
    await session.flush()
    return PromotionPreferences(
        promotion_emails_enabled=user.promotion_emails_enabled
    )


@router.get("/analytics", response_model=PromotionAnalytics, tags=[APITag.private])
async def get_analytics(
    auth_subject: auth.PromotionUser,
    days: int = Query(30, ge=1, le=365, description="Trailing window for the chart."),
    session: AsyncReadSession = Depends(get_db_read_session),
) -> PromotionAnalytics:
    """Promotion analytics for the dashboard: KPI totals (spend, impressions,
    clicks, CTR) plus a daily series, scoped to the requesting user. Totals come
    from the Postgres counters; the daily series is read from the Tinybird
    ``promotion_analytics`` pipe when configured (which adds per-day impressions
    and clicks), otherwise from a Postgres spend-only series."""
    author_id = auth_subject.subject.id
    end = utc_now()
    start = end - timedelta(days=days)
    totals, series = await promotion_service.analytics(
        session, author_id=author_id, start=start, end=end
    )
    impressions = int(totals.total_impressions)
    clicks = int(totals.total_clicks)

    tinybird_series = await promotion_service.analytics_timeseries_tinybird(
        author_id=author_id, days=days
    )
    if tinybird_series is not None:
        periods = [
            PromotionAnalyticsPeriod(
                timestamp=row["timestamp"],
                spend_cents=int(row.get("spend_cents") or 0),
                promotions=int(row.get("promotions") or 0),
                impressions=int(row.get("impressions") or 0),
                clicks=int(row.get("clicks") or 0),
            )
            for row in tinybird_series
        ]
    else:
        periods = [
            PromotionAnalyticsPeriod(
                timestamp=row.bucket,
                spend_cents=int(row.spend_cents),
                promotions=int(row.promotions),
            )
            for row in series
        ]

    return PromotionAnalytics(
        total_promotions=int(totals.total_promotions),
        total_spend_cents=int(totals.total_spend_cents),
        total_impressions=impressions,
        total_clicks=clicks,
        ctr=(clicks / impressions) if impressions else 0.0,
        periods=periods,
    )


@router.get("/{promotion_id}/click", tags=[APITag.public])
async def click_promotion(
    request: Request,
    promotion_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> RedirectResponse:
    """Track a click and redirect to the promotion's link. Falls back to the
    news wall when the promotion has no link or doesn't exist. The click is
    deduped per viewer (the redirect always happens)."""
    link = await promotion_service.track_click(
        session, promotion_id, redis=redis, viewer_key=_viewer_key(request)
    )
    return RedirectResponse(url=link or settings.FRONTEND_BASE_URL, status_code=302)


@router.post("/", response_model=PromotionCheckout, tags=[APITag.private])
async def create_promotion(
    data: PromotionCreate,
    auth_subject: auth.PromotionUserWrite,
    session: AsyncSession = Depends(get_db_session),
) -> PromotionCheckout:
    """Buy a promotion: creates the draft and returns a hosted checkout URL. The
    promotion joins its category's queue once the order webhook confirms
    payment."""
    if not settings.PROMOTION_PRODUCT_ID:
        raise PromotionUnavailable()
    promotion = await promotion_service.create_pending(
        session,
        author_id=auth_subject.subject.id,
        category=data.category,
        title=data.title,
        body=data.body,
        link=data.link,
        image_url=data.image_url,
        blocks=data.blocks,
    )
    url = await billing_service.create_promotion_checkout(
        auth_subject,
        promotion_id=promotion.id,
        amount_cents=promotion.amount_cents,
    )
    return PromotionCheckout(promotion_id=promotion.id, url=url)
