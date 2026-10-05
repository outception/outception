"""Who asked for a morning briefing: one row per device and profile, keyed
by the push endpoint (web) or the device token (app). No account is
involved; the endpoint is the only identity."""

from datetime import date
from typing import Any

from sqlalchemy import Date, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from outception.kit.db.models import RecordModel


class PushSubscription(RecordModel):
    __tablename__ = "push_subscriptions"
    __table_args__ = (
        UniqueConstraint("profile_id", "endpoint", name="uq_push_subscription"),
    )

    profile_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # web | app
    kind: Mapped[str] = mapped_column(String(8), nullable=False)
    # The push service endpoint on the web; the device token in the app.
    endpoint: Mapped[str] = mapped_column(Text, nullable=False)
    # The web subscription's encryption keys (p256dh, auth); null in the app.
    keys: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    # The UTC day of the last briefing sent, so a day carries one push at most.
    last_sent_for: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Consecutive delivery failures; the row goes after a few.
    failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
