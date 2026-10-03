from typing import Any
from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from outception.kit.db.models import RecordModel


class ReaderPref(RecordModel):
    """One preference of a signed-in reader, keyed by name: focused and
    hidden cards, chosen Starters and briefing profiles, theme. Anonymous
    readers keep the same keys in local storage; logging in syncs them."""

    __tablename__ = "reader_prefs"
    __table_args__ = (UniqueConstraint("user_id", "key", name="uq_reader_pref"),)

    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="cascade"),
        nullable=False,
        index=True,
    )
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[Any] = mapped_column(JSONB, nullable=False)
