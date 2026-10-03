"""What readers tell us through the feedback sheet: one text field and an
optional email, scrubbed before it is stored, kept 180 days."""

from typing import Any

from sqlalchemy import Boolean, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from outception.kit.db.models import RecordModel


class Feedback(RecordModel):
    __tablename__ = "feedback"

    message: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    # web | app
    surface: Mapped[str] = mapped_column(String(16), nullable=False)
    # Where the sheet was opened: page, card id, app version.
    context: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    # A keyed hash of the sender's address, for abuse review only.
    sender_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Whether the daily digest has carried it.
    digested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
