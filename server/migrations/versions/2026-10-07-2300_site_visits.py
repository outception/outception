"""site visits

Revision ID: d6f2b8c4a1e3
Revises: c5e1a7d3f9b2
Create Date: 2026-10-07 23:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# Outception Custom Imports

# revision identifiers, used by Alembic.
revision = "d6f2b8c4a1e3"
down_revision = "c5e1a7d3f9b2"
branch_labels: tuple[str] | None = None
depends_on: tuple[str] | None = None


def upgrade() -> None:
    # Ensures we don't break app by applying a deadlock-inducing migration.
    # CREATE INDEX CONCURRENTLY needs its own, far larger timeout -- see ADR-0006.
    op.execute("SET LOCAL lock_timeout = '5s'")
    # Site visits by day and page path or visitor country, as the counter
    # reports them; the founder's reach chart races these.
    op.create_table(
        "site_visits",
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("dimension", sa.String(length=16), nullable=False),
        sa.Column("key", sa.String(length=200), nullable=False),
        sa.Column("views", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("modified_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("site_visits_pkey")),
    )
    op.create_index(
        op.f("ix_site_visits_created_at"), "site_visits", ["created_at"], unique=False
    )
    op.create_index(
        op.f("ix_site_visits_deleted_at"), "site_visits", ["deleted_at"], unique=False
    )
    op.create_index(
        "ix_site_visits_day_dimension_key",
        "site_visits",
        ["day", "dimension", "key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_site_visits_day_dimension_key", table_name="site_visits")
    op.drop_index(op.f("ix_site_visits_deleted_at"), table_name="site_visits")
    op.drop_index(op.f("ix_site_visits_created_at"), table_name="site_visits")
    op.drop_table("site_visits")
