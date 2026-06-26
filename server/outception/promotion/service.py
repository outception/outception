from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

import httpx
import structlog
from sqlalchemy import Row

from outception.config import settings
from outception.integrations.tinybird import tinybird_client
from outception.kit.utils import utc_now
from outception.logging import Logger
from outception.models import Promotion
from outception.models.promotion import PromotionStatus
from outception.postgres import AsyncReadSession, AsyncSession
from outception.redis import Redis

from . import events, notifications
from .repository import PromotionRepository

log: Logger = structlog.get_logger()

# Pricing/duration, sourced from config so they're tunable per-environment.
BLOCK_MINUTES = settings.PROMOTION_BLOCK_MINUTES
PRICE_CENTS_PER_BLOCK = settings.PROMOTION_PRICE_CENTS


class PromotionService:
    """Pay-to-post promotions and the per-category featured-slot queue.

    The queue is a lazy state machine: it advances on payment and on every
    public read. Each advance row-locks the category to stay correct under
    concurrency. A periodic ``sweep`` complements the lazy advance so a paid
    slot still expires and the next promotion goes live (with its emails) even
    in a category with zero traffic.
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
        self,
        session: AsyncSession,
        promotion_id: UUID,
        *,
        external_ref: str,
        paid_amount_cents: int | None = None,
    ) -> None:
        """Mark a paid promotion ``queued`` and advance its category. Idempotent
        on ``external_ref`` (the order ref), so a redelivered webhook is a
        no-op.

        When ``paid_amount_cents`` is given (the webhook path), the order must
        have paid at least the promotion's price; an underpayment is refused so
        the slot can't be bought below cost. ``None`` skips the check for
        internal callers that already trust the amount."""
        repo = PromotionRepository.from_session(session)
        existing = await repo.get_by_payment_ref(external_ref)
        if existing is not None:
            return
        # Lock the row so a concurrently-redelivered webhook can't also pass the
        # PENDING_PAYMENT check and activate this promotion twice.
        promotion = await repo.get_by_id_for_update(promotion_id)
        if promotion is None or promotion.status != PromotionStatus.PENDING_PAYMENT:
            return
        if paid_amount_cents is not None and paid_amount_cents < promotion.amount_cents:
            log.warning(
                "promotion.activate_paid.underpaid",
                promotion_id=str(promotion_id),
                external_ref=external_ref,
                expected_cents=promotion.amount_cents,
                paid_cents=paid_amount_cents,
            )
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

        # _advance promotes the first queued promotion when the slot is free;
        # if this one is still queued, the slot was occupied — let the buyer know
        # their paid promotion is waiting (it gets an "activated" email later).
        refreshed = await repo.get_by_id(promotion_id)
        if refreshed is not None and refreshed.status == PromotionStatus.QUEUED:
            notifications.notify(refreshed, "queued")

    async def _advance(
        self, session: AsyncSession, category: str, *, now: datetime
    ) -> None:
        """Expire a finished active slot and promote the next queued promotion.
        Row-locks the category's open rows for the duration."""
        repo = PromotionRepository.from_session(session)
        rows = list(await repo.lock_category_open(category))

        active = next((p for p in rows if p.status == PromotionStatus.ACTIVE), None)
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
            notifications.notify(active, "expired")
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
        notifications.notify(nxt, "activated")

    async def sweep(self, session: AsyncSession) -> None:
        """Advance every open category's queue on a schedule, so an expired slot
        rolls over to the next promotion (and the expiry/activation emails fire)
        even when no one is reading that category's wall."""
        now = utc_now()
        repo = PromotionRepository.from_session(session)
        for category in await repo.list_open_categories():
            await self._advance(session, category, now=now)

    async def get_featured(
        self,
        session: AsyncSession,
        categories: Sequence[str],
        *,
        redis: Redis | None = None,
        viewer_key: str | None = None,
    ) -> Sequence[Promotion]:
        """The active promotion for each category (advancing each queue first).
        Tallies one impression per served promotion for analytics.

        When ``redis`` and ``viewer_key`` are given (the public endpoint), a
        viewer counts at most one impression per promotion within the dedup
        window, so background polling of the wall doesn't inflate the count.
        Callers without that context (internal/tests) count every serve."""
        now = utc_now()
        repo = PromotionRepository.from_session(session)
        for category in categories:
            await self._advance(session, category, now=now)
        active = await repo.list_active_for_categories(categories)
        countable = await self._dedup_impressions(redis, viewer_key, active)
        if countable:
            await repo.increment_impressions([p.id for p in countable])
            events.emit_many(
                [
                    events.build_event(p, events.PromotionEventName.impression)
                    for p in countable
                ]
            )
        return active

    async def _claim_viewer_event(
        self,
        redis: Redis | None,
        viewer_key: str | None,
        *,
        kind: str,
        promotion_id: UUID,
    ) -> bool:
        """Whether this (kind, promotion, viewer) should be counted: True the
        first time within the dedup window, then False until it lapses (claimed
        via ``SET NX EX``). Without a viewer context or with dedup disabled,
        always True. Keeps impressions and clicks counted on the same basis so
        CTR stays meaningful (a viewer can't click more than they're shown)."""
        window = settings.PROMOTION_IMPRESSION_DEDUP_SECONDS
        if redis is None or viewer_key is None or window <= 0:
            return True
        key = f"promotion:{kind}:{promotion_id}:{viewer_key}"
        return bool(await redis.set(key, "1", nx=True, ex=window))

    async def _dedup_impressions(
        self,
        redis: Redis | None,
        viewer_key: str | None,
        promotions: Sequence[Promotion],
    ) -> list[Promotion]:
        """Of ``promotions``, the ones this viewer hasn't been counted for
        within the dedup window, so background polling can't inflate the count."""
        fresh: list[Promotion] = []
        for promotion in promotions:
            if await self._claim_viewer_event(
                redis, viewer_key, kind="impression", promotion_id=promotion.id
            ):
                fresh.append(promotion)
        return fresh

    async def track_click(
        self,
        session: AsyncSession,
        promotion_id: UUID,
        *,
        redis: Redis | None = None,
        viewer_key: str | None = None,
    ) -> str | None:
        """Return the promotion's outbound link (or ``None`` if it has none / the
        promotion doesn't exist), counting a click at most once per viewer within
        the dedup window. The redirect always happens; only the counter is
        deduped, mirroring impressions so CTR can't exceed 100%."""
        repo = PromotionRepository.from_session(session)
        promotion = await repo.get_by_id(promotion_id)
        if promotion is None:
            return None
        if await self._claim_viewer_event(
            redis, viewer_key, kind="click", promotion_id=promotion_id
        ):
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
        active = next(iter(await repo.list_active_for_categories([category])), None)
        queued = await repo.list_queue(category)
        return active, queued

    async def list_mine(
        self, session: AsyncReadSession | AsyncSession, author_id: UUID
    ) -> Sequence[Promotion]:
        return await PromotionRepository.from_session(session).list_by_author(author_id)


promotion = PromotionService()
