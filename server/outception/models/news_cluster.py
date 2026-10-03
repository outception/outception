"""The same story across publishers: a cluster, its members, its scores
per profile, and the briefings built from them."""

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    TIMESTAMP,
    Date,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from outception.kit.db.models import IDModel, Model, RecordModel


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


class NewsClusterScore(Model):
    __tablename__ = "news_cluster_scores"

    cluster_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("news_clusters.id", ondelete="cascade"),
        primary_key=True,
    )
    profile_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    # 0 to 10; null when the model failed twice.
    score: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # One sentence from the contract, scrubbed.
    why: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Which lane entry answered.
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    tokens_in: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    scored_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, index=True
    )
    # The publisher count at scoring time: a cluster is re-scored within a
    # day only when it has doubled since.
    publisher_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class NewsBriefing(IDModel):
    __tablename__ = "news_briefings"
    __table_args__ = (
        UniqueConstraint(
            "profile_id", "built_for", "built_at", name="uq_news_briefing_build"
        ),
    )

    profile_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # The UTC day the briefing was built for.
    built_for: Mapped[date] = mapped_column(Date, nullable=False)
    built_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, index=True
    )
    # The ordered item list, frozen at build time.
    items: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    # Counts per category, nulls, spend.
    stats: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
