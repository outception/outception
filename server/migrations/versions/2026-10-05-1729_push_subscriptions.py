"""push subscriptions

Revision ID: 7c1e5a9d2b40
Revises: 46d6516de288
Create Date: 2026-10-05 17:29:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# Outception Custom Imports

# revision identifiers, used by Alembic.
revision = "7c1e5a9d2b40"
down_revision = "46d6516de288"
branch_labels: tuple[str] | None = None
depends_on: tuple[str] | None = None


def upgrade() -> None:
    # Ensures we don't break app by applying a deadlock-inducing migration.
    # CREATE INDEX CONCURRENTLY needs its own, far larger timeout -- see ADR-0006.
    op.execute("SET LOCAL lock_timeout = '5s'")
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


def downgrade() -> None:
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
