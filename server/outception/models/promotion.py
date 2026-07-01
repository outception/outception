from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import TIMESTAMP, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship

from outception.kit.db.models import RecordModel
from outception.models.user import User


class PromotionStatus(StrEnum):
    """Lifecycle of a paid promotion.

    ``pending_payment`` → (order webhook) → ``queued`` → (its turn in the
    category's featured slot) → ``active`` → (its time runs out) → ``expired``.
    ``rejected`` is reserved for the future pre-publication review gate.
    """

    PENDING_PAYMENT = "pending_payment"
    QUEUED = "queued"
    ACTIVE = "active"
    EXPIRED = "expired"
    REJECTED = "rejected"


class Promotion(RecordModel):
    """A paid post that rents exclusive time in one category's featured slot.

    The product is *distribution*, not access: anyone reads the wall for free,
    but to be the "in focus" promotion for a category you pay
    ``PROMOTION_PRICE_CENTS`` per ``PROMOTION_BLOCK_MINUTES`` (buyable in
    multiples → ``duration_minutes``). Each category has at most one ``active``
    promotion at a time; the rest wait ``queued`` in first-paid-first-served
    order and surface as in-feed "Promoted" cards until their turn. When the
    active slot's ``active_until`` passes, the next queued promotion is promoted
    (see ``PromotionService._advance``). See
    handbook/engineering/design-documents/post-review-credits.mdx for the
    sibling credit economy this reuses the billing plumbing of.
    """

    __tablename__ = "promotions"

    author_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # The featured slot a promotion competes for (one of the news wall's
    # category ids, e.g. "tech"). Indexed: every queue operation filters by it.
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    link: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    # Purchased featured time (a multiple of PROMOTION_BLOCK_MINUTES) and what
    # it cost, frozen at creation so later config changes don't rewrite history.
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=PromotionStatus.PENDING_PAYMENT,
        default=PromotionStatus.PENDING_PAYMENT,
        index=True,
    )
    # The gateway order ref (``order:<id>``) that paid for this promotion.
    # Unique so a redelivered order webhook can't activate it twice.
    payment_ref: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True
    )
    paid_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    activated_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    # When the active slot frees up. Indexed: the queue advance scans for
    # active rows whose window has elapsed.
    active_until: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, index=True
    )
    # Engagement counters for promotion analytics: impressions are tallied when
    # the promotion is served as a category's featured slot; clicks when a
    # reader follows its link through the tracked redirect.
    impressions: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0", default=0
    )
    clicks: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0", default=0
    )

    @declared_attr
    def author(cls) -> "Mapped[User]":
        return relationship("User", lazy="raise")
