from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

import httpx
import structlog
from sqlalchemy import Row

from polar.config import settings
from polar.integrations.tinybird import tinybird_client
from polar.kit.utils import utc_now
from polar.logging import Logger
from polar.models import Promotion
from polar.models.promotion import PromotionStatus
from polar.postgres import AsyncReadSession, AsyncSession

from . import events
from .repository import PromotionRepository

log: Logger = structlog.get_logger()

# Pricing/duration, sourced from config so they're tunable per-environment.
BLOCK_MINUTES = settings.PROMOTION_BLOCK_MINUTES
PRICE_CENTS_PER_BLOCK = settings.PROMOTION_PRICE_CENTS


class PromotionService:
    """Pay-to-post promotions and the per-category featured-slot queue.

    The queue is a lazy state machine: it advances on payment and on every
    public read, so no scheduled job is required for the common (someone's
    looking) case. Each advance row-locks the category to stay correct under
    concurrency. A background sweep could complement this to honour a buyer's
    window even with zero traffic — left as a follow-up.
    """

    async def create_pending(
        self,
        session: AsyncSession,
        *,
        author_id: UUID,
        category: str,
        title: str,
        body: str,
        link: str | None,
        image_url: str | None,
        blocks: int,
    ) -> Promotion:
        """Create the unpaid draft. It enters the queue only once the order
        webhook confirms payment (see ``activate_paid``)."""
        blocks = max(1, blocks)
        promotion = Promotion(
            author_id=author_id,
            category=category,
            title=title,
            body=body,
            link=link,
            image_url=image_url,
            duration_minutes=blocks * BLOCK_MINUTES,
            amount_cents=blocks * PRICE_CENTS_PER_BLOCK,
            status=PromotionStatus.PENDING_PAYMENT,
        )
        promotion = await PromotionRepository.from_session(session).create(
            promotion, flush=True
        )
        events.emit(promotion, events.PromotionEventName.created)
        return promotion

    async def activate_paid(
        self, session: AsyncSession, promotion_id: UUID, *, external_ref: str
    ) -> None:
        """Mark a paid promotion ``queued`` and advance its category. Idempotent
        on ``external_ref`` (the order ref), so a redelivered webhook is a
        no-op."""
        repo = PromotionRepository.from_session(session)
        existing = await repo.get_by_payment_ref(external_ref)
        if existing is not None:
            return
        promotion = await repo.get_by_id(promotion_id)
        if promotion is None or promotion.status != PromotionStatus.PENDING_PAYMENT:
            return
        now = utc_now()
        await repo.update(
            promotion,
            update_dict={
                "status": PromotionStatus.QUEUED,
                "paid_at": now,
                "payment_ref": external_ref,
            },
            flush=True,
        )
        events.emit(promotion, events.PromotionEventName.paid)
        await self._advance(session, promotion.category, now=now)

    async def _advance(
        self, session: AsyncSession, category: str, *, now: datetime
    ) -> None:
        """Expire a finished active slot and promote the next queued promotion.
        Row-locks the category's open rows for the duration."""
        repo = PromotionRepository.from_session(session)
        rows = list(await repo.lock_category_open(category))

        active = next(
            (p for p in rows if p.status == PromotionStatus.ACTIVE), None
        )
        if (
            active is not None
            and active.active_until is not None
            and active.active_until <= now
        ):
            await repo.update(
                active,
                update_dict={"status": PromotionStatus.EXPIRED},
                flush=True,
            )
            events.emit(active, events.PromotionEventName.expired)
            active = None
        if active is not None:
            return  # slot still occupied — nothing to promote

        queued = [p for p in rows if p.status == PromotionStatus.QUEUED]
        if not queued:
            return
        nxt = queued[0]  # lock_category_open already ordered first-paid-first
        await repo.update(
            nxt,
            update_dict={
                "status": PromotionStatus.ACTIVE,
                "activated_at": now,
                "active_until": now + timedelta(minutes=nxt.duration_minutes),
            },
            flush=True,
        )
        events.emit(nxt, events.PromotionEventName.activated)

    async def get_featured(
        self, session: AsyncSession, categories: Sequence[str]
    ) -> Sequence[Promotion]:
        """The active promotion for each category (advancing each queue first).
        Tallies one impression per served promotion for analytics."""
        now = utc_now()
        repo = PromotionRepository.from_session(session)
        for category in categories:
            await self._advance(session, category, now=now)
        active = await repo.list_active_for_categories(categories)
        await repo.increment_impressions([p.id for p in active])
        events.emit_many(
            [
                events.build_event(p, events.PromotionEventName.impression)
                for p in active
            ]
        )
        return active

    async def track_click(
        self, session: AsyncSession, promotion_id: UUID
    ) -> str | None:
        """Record a click and return the promotion's outbound link (or ``None``
        if it has none / the promotion doesn't exist)."""
        repo = PromotionRepository.from_session(session)
        promotion = await repo.get_by_id(promotion_id)
        if promotion is None:
            return None
        await repo.increment_click(promotion_id)
        events.emit(promotion, events.PromotionEventName.click)
        return promotion.link

    async def analytics(
        self,
        session: AsyncReadSession | AsyncSession,
        *,
        author_id: UUID | None,
        start: datetime,
        end: datetime,
    ) -> tuple[Row[tuple[Any, ...]], Sequence[Row[tuple[Any, ...]]]]:
        """Promotion analytics: aggregate totals + a daily spend series. Scope to
        ``author_id`` for a promoter's own view, ``None`` for platform-wide."""
        repo = PromotionRepository.from_session(session)
        totals = await repo.analytics_totals(author_id)
        series = await repo.analytics_timeseries(author_id, start=start, end=end)
        return totals, series

    async def analytics_timeseries_tinybird(
        self, *, author_id: UUID | None, days: int, category: str | None = None
    ) -> list[dict[str, Any]] | None:
        """Daily promotion metrics (spend/impressions/clicks/promotions) from the
        Tinybird ``promotion_analytics`` pipe — the only source with per-day
        impression/click counts. Returns ``None`` when Tinybird isn't configured
        or the query fails, so callers can fall back to the Postgres series."""
        if not settings.is_tinybird_configured():
            return None
        params: dict[str, Any] = {"days": days}
        if author_id is not None:
            params["author_id"] = str(author_id)
        if category is not None:
            params["category"] = category
        try:
            return await tinybird_client.query_pipe(
                events.PROMOTION_ANALYTICS_PIPE, params
            )
        except httpx.HTTPError:
            log.warning("promotion.analytics.tinybird_failed", author_id=author_id)
            return None

    async def get_category(
        self, session: AsyncSession, category: str
    ) -> tuple[Promotion | None, Sequence[Promotion]]:
        """A category's active promotion plus its queued in-feed promotions."""
        await self._advance(session, category, now=utc_now())
        repo = PromotionRepository.from_session(session)
        active = next(
            iter(await repo.list_active_for_categories([category])), None
        )
        queued = await repo.list_queue(category)
        return active, queued

    async def list_mine(
        self, session: AsyncReadSession | AsyncSession, author_id: UUID
    ) -> Sequence[Promotion]:
        return await PromotionRepository.from_session(session).list_by_author(
            author_id
        )


promotion = PromotionService()
