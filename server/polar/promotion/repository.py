from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Row, func, select, update

from polar.kit.repository import RepositoryBase
from polar.models import Promotion
from polar.models.promotion import PromotionStatus

# First-paid wins; created_at breaks ties (and orders rows with no paid_at yet).
_QUEUE_ORDER = (Promotion.paid_at.asc(), Promotion.created_at.asc())


class PromotionRepository(RepositoryBase[Promotion]):
    model = Promotion

    async def get_by_id(self, promotion_id: UUID) -> Promotion | None:
        statement = (
            self.get_base_statement()
            .where(Promotion.id == promotion_id)
            .execution_options(populate_existing=True)
        )
        return await self.get_one_or_none(statement)

    async def get_by_id_for_update(self, promotion_id: UUID) -> Promotion | None:
        """Row-locked fetch (``FOR UPDATE``). Used by ``activate_paid`` so the
        PENDING_PAYMENT -> QUEUED transition is atomic: a concurrently
        redelivered order webhook blocks here, then sees the already-paid status
        and becomes a no-op instead of activating the promotion twice."""
        statement = (
            self.get_base_statement()
            .where(Promotion.id == promotion_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return await self.get_one_or_none(statement)

    async def get_by_payment_ref(self, payment_ref: str) -> Promotion | None:
        statement = self.get_base_statement().where(
            Promotion.payment_ref == payment_ref
        )
        return await self.get_one_or_none(statement)

    async def lock_category_open(self, category: str) -> Sequence[Promotion]:
        """The active + queued rows for a category, row-locked and oldest-paid
        first. ``FOR UPDATE`` serialises concurrent queue advances so the slot
        can never be handed to two promotions at once (write session only)."""
        statement = (
            select(Promotion)
            .where(
                Promotion.category == category,
                Promotion.status.in_([PromotionStatus.ACTIVE, PromotionStatus.QUEUED]),
            )
            .order_by(*_QUEUE_ORDER)
            .with_for_update()
        )
        return await self.get_all(statement)

    async def list_open_categories(self) -> Sequence[str]:
        """Distinct categories with an active or queued promotion — the only
        ones a queue advance could affect."""
        statement = (
            select(Promotion.category)
            .where(
                Promotion.status.in_([PromotionStatus.ACTIVE, PromotionStatus.QUEUED])
            )
            .distinct()
        )
        result = await self.session.execute(statement)
        return result.scalars().all()

    async def list_active_for_categories(
        self, categories: Sequence[str]
    ) -> Sequence[Promotion]:
        statement = self.get_base_statement().where(
            Promotion.category.in_(list(categories)),
            Promotion.status == PromotionStatus.ACTIVE,
        )
        return await self.get_all(statement)

    async def list_queue(self, category: str) -> Sequence[Promotion]:
        statement = (
            self.get_base_statement()
            .where(
                Promotion.category == category,
                Promotion.status == PromotionStatus.QUEUED,
            )
            .order_by(*_QUEUE_ORDER)
        )
        return await self.get_all(statement)

    async def list_by_author(self, author_id: UUID) -> Sequence[Promotion]:
        statement = (
            self.get_base_statement()
            .where(Promotion.author_id == author_id)
            .order_by(Promotion.created_at.desc())
        )
        return await self.get_all(statement)

    async def increment_impressions(self, promotion_ids: Sequence[UUID]) -> None:
        """Tally one impression for each currently-served promotion. Done in a
        single set-based UPDATE so serving the wall stays cheap."""
        if not promotion_ids:
            return
        await self.session.execute(
            update(Promotion)
            .where(Promotion.id.in_(list(promotion_ids)))
            .values(impressions=Promotion.impressions + 1)
        )

    async def increment_click(self, promotion_id: UUID) -> None:
        await self.session.execute(
            update(Promotion)
            .where(Promotion.id == promotion_id)
            .values(clicks=Promotion.clicks + 1)
        )

    async def analytics_totals(self, author_id: UUID | None) -> Row[tuple[Any, ...]]:
        """Aggregate spend/impressions/clicks. Scope to one author for a
        promoter's own view, or pass ``None`` for the platform-wide total."""
        paid = Promotion.paid_at.isnot(None)
        statement = select(
            func.count().filter(paid).label("total_promotions"),
            func.coalesce(func.sum(Promotion.amount_cents).filter(paid), 0).label(
                "total_spend_cents"
            ),
            func.coalesce(func.sum(Promotion.impressions), 0).label(
                "total_impressions"
            ),
            func.coalesce(func.sum(Promotion.clicks), 0).label("total_clicks"),
        )
        if author_id is not None:
            statement = statement.where(Promotion.author_id == author_id)
        result = await self.session.execute(statement)
        return result.one()

    async def analytics_timeseries(
        self, author_id: UUID | None, *, start: datetime, end: datetime
    ) -> Sequence[Row[tuple[Any, ...]]]:
        """Daily spend and promotion count, bucketed on ``paid_at`` (so a bucket
        reflects money actually taken that day)."""
        bucket = func.date_trunc("day", Promotion.paid_at).label("bucket")
        statement = (
            select(
                bucket,
                func.coalesce(func.sum(Promotion.amount_cents), 0).label("spend_cents"),
                func.count().label("promotions"),
            )
            .where(
                Promotion.paid_at.isnot(None),
                Promotion.paid_at >= start,
                Promotion.paid_at <= end,
            )
            .group_by(bucket)
            .order_by(bucket)
        )
        if author_id is not None:
            statement = statement.where(Promotion.author_id == author_id)
        result = await self.session.execute(statement)
        return result.all()
