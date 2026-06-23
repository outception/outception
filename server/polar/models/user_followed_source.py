from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from polar.kit.db.models import RecordModel


class UserFollowedSource(RecordModel):
    """A user following a news source — powers the personalised "Following"
    view on the wall."""

    __tablename__ = "user_followed_sources"
    __table_args__ = (
        UniqueConstraint("user_id", "source_id", name="uq_user_followed_source"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="cascade"),
        nullable=False,
        index=True,
    )
    source_id: Mapped[str] = mapped_column(String(128), nullable=False)
