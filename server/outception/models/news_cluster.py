"""The same story across publishers: a cluster and its members."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import TIMESTAMP, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from outception.kit.db.models import Model, RecordModel


class NewsCluster(RecordModel):
    __tablename__ = "news_clusters"

    # The canonical URL key of the seed item, or the signature bucket id.
    key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    # The representative headline: the longest common one, else the first
    # seen.
    title: Mapped[str] = mapped_column(Text, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, index=True
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, index=True
    )
    # Distinct source ids among the members.
    publisher_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    member_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # The source that first carried it: the lead outlet of the coverage line.
    lead_source_id: Mapped[str] = mapped_column(String(128), nullable=False)


class NewsClusterMember(Model):
    __tablename__ = "news_cluster_members"
    __table_args__ = (
        Index("ix_news_cluster_members_url_key", "url_key"),
        Index("ix_news_cluster_members_seen_at", "seen_at"),
    )

    cluster_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("news_clusters.id", ondelete="cascade"),
        primary_key=True,
    )
    source_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    # The item's id within its source.
    item_id: Mapped[str] = mapped_column(String(2048), primary_key=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    url_key: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    pub_date: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    seen_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
