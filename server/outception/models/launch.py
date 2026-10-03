from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from outception.kit.db.models import RecordModel
from outception.kit.extensions.sqlalchemy import StringEnum


class LaunchStatus(StrEnum):
    """A product moves submitted -> approved (into a day) -> live (that day
    arrives) -> ended (the day passes). The submitter can withdraw before it
    is live; the founder can reject at any point before it is live."""

    submitted = "submitted"
    approved = "approved"
    live = "live"
    ended = "ended"
    rejected = "rejected"
    withdrawn = "withdrawn"


class Launch(RecordModel):
    """A product submitted to the Products of the day card. Nothing is
    visible before the founder approves it into a day; five a day at most."""

    __tablename__ = "launches"
    __table_args__ = (
        Index(
            "ix_launches_day_position",
            "day",
            "position",
            unique=True,
            postgresql_where="state IN ('approved', 'live')",
        ),
        Index("ix_launches_state_day", "state", "day"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="cascade"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    tagline: Mapped[str] = mapped_column(String(140), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    logo_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    kicker: Mapped[str] = mapped_column(String(16), nullable=False, default="new")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    contact_email: Mapped[str] = mapped_column(String(320), nullable=False)
    state: Mapped[LaunchStatus] = mapped_column(
        StringEnum(LaunchStatus), nullable=False, default=LaunchStatus.submitted
    )
    featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    day: Mapped[date | None] = mapped_column(Date, nullable=True)
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reviewer_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
