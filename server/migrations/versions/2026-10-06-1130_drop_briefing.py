"""drop briefing

Revision ID: 9e4b7a1c3d52
Revises: 3f8a2c7d9e11
Create Date: 2026-10-06 11:30:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Outception Custom Imports

# revision identifiers, used by Alembic.
revision = "9e4b7a1c3d52"
down_revision = "3f8a2c7d9e11"
branch_labels: tuple[str] | None = None
depends_on: tuple[str] | None = None


def upgrade() -> None:
    # Ensures we don't break app by applying a deadlock-inducing migration.
    # CREATE INDEX CONCURRENTLY needs its own, far larger timeout -- see ADR-0006.
    op.execute("SET LOCAL lock_timeout = '5s'")
    # The briefing is gone from the product: the built briefings, the per
    # profile cluster scores and the push subscriptions go with it.
    op.drop_index(
        op.f("ix_push_subscriptions_profile_id"), table_name="push_subscriptions"
    )
    op.drop_index(
        op.f("ix_push_subscriptions_deleted_at"), table_name="push_subscriptions"
    )
    op.drop_index(
        op.f("ix_push_subscriptions_created_at"), table_name="push_subscriptions"
    )
    op.drop_table("push_subscriptions")
    op.drop_index(
        op.f("ix_news_cluster_scores_scored_at"), table_name="news_cluster_scores"
    )
    op.drop_table("news_cluster_scores")
    op.drop_index(op.f("ix_news_briefings_profile_id"), table_name="news_briefings")
    op.drop_index(op.f("ix_news_briefings_built_at"), table_name="news_briefings")
    op.drop_table("news_briefings")


def downgrade() -> None:
    # Ensures we don't break app by applying a deadlock-inducing migration.
    # CREATE INDEX CONCURRENTLY needs its own, far larger timeout -- see ADR-0006.
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.create_table(
        "news_briefings",
        sa.Column("profile_id", sa.String(length=64), nullable=False),
        sa.Column("built_for", sa.Date(), nullable=False),
        sa.Column("built_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("items", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("stats", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("news_briefings_pkey")),
        sa.UniqueConstraint(
            "profile_id", "built_for", "built_at", name="uq_news_briefing_build"
        ),
    )
    op.create_index(
        op.f("ix_news_briefings_built_at"), "news_briefings", ["built_at"], unique=False
    )
    op.create_index(
        op.f("ix_news_briefings_profile_id"),
        "news_briefings",
        ["profile_id"],
        unique=False,
    )
    op.create_table(
        "news_cluster_scores",
        sa.Column("cluster_id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.String(length=64), nullable=False),
        sa.Column("score", sa.SmallInteger(), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column("why", sa.Text(), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("tokens_in", sa.Integer(), nullable=False),
        sa.Column("tokens_out", sa.Integer(), nullable=False),
        sa.Column("scored_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("publisher_count", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["cluster_id"],
            ["news_clusters.id"],
            name=op.f("news_cluster_scores_cluster_id_fkey"),
            ondelete="cascade",
        ),
        sa.PrimaryKeyConstraint(
            "cluster_id", "profile_id", name=op.f("news_cluster_scores_pkey")
        ),
    )
    op.create_index(
        op.f("ix_news_cluster_scores_scored_at"),
        "news_cluster_scores",
        ["scored_at"],
        unique=False,
    )
    op.create_table(
        "push_subscriptions",
        sa.Column("profile_id", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=8), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("keys", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("last_sent_for", sa.Date(), nullable=True),
        sa.Column("failures", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("modified_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("push_subscriptions_pkey")),
        sa.UniqueConstraint("profile_id", "endpoint", name="uq_push_subscription"),
    )
    op.create_index(
        op.f("ix_push_subscriptions_created_at"),
        "push_subscriptions",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_push_subscriptions_deleted_at"),
        "push_subscriptions",
        ["deleted_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_push_subscriptions_profile_id"),
        "push_subscriptions",
        ["profile_id"],
        unique=False,
    )
