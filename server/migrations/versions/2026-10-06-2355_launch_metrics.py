"""launch metrics

Revision ID: b4d8f2a6c1e7
Revises: 9e4b7a1c3d52
Create Date: 2026-10-06 23:55:00.000000

"""

import sqlalchemy as sa
from alembic import op

# Outception Custom Imports

# revision identifiers, used by Alembic.
revision = "b4d8f2a6c1e7"
down_revision = "9e4b7a1c3d52"
branch_labels: tuple[str] | None = None
depends_on: tuple[str] | None = None


def upgrade() -> None:
    # Ensures we don't break app by applying a deadlock-inducing migration.
    # CREATE INDEX CONCURRENTLY needs its own, far larger timeout -- see ADR-0006.
    op.execute("SET LOCAL lock_timeout = '5s'")
    # A product's reach by day: the submitter sees views and clicks.
    op.create_table(
        "launch_metrics",
        sa.Column("launch_id", sa.Uuid(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("views", sa.Integer(), nullable=False),
        sa.Column("clicks", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("modified_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["launch_id"],
            ["launches.id"],
            name=op.f("launch_metrics_launch_id_fkey"),
            ondelete="cascade",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("launch_metrics_pkey")),
    )
    op.create_index(
        "ix_launch_metrics_launch_day",
        "launch_metrics",
        ["launch_id", "day"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_launch_metrics_launch_day", table_name="launch_metrics")
    op.drop_table("launch_metrics")
