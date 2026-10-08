"""site visits index led by dimension

Revision ID: e7a3c9d5b2f4
Revises: d6f2b8c4a1e3
Create Date: 2026-10-07 23:30:00.000000

"""

from alembic import op

# Outception Custom Imports

# revision identifiers, used by Alembic.
revision = "e7a3c9d5b2f4"
down_revision = "d6f2b8c4a1e3"
branch_labels: tuple[str] | None = None
depends_on: tuple[str] | None = None


def upgrade() -> None:
    # Ensures we don't break app by applying a deadlock-inducing migration.
    # CREATE INDEX CONCURRENTLY needs its own, far larger timeout -- see ADR-0006.
    op.execute("SET LOCAL lock_timeout = '5s'")
    # The race reads one dimension over a day range: lead the unique index
    # with the dimension so a read never scans the other one.
    op.create_index(
        "ix_site_visits_dimension_day_key",
        "site_visits",
        ["dimension", "day", "key"],
        unique=True,
    )
    op.drop_index("ix_site_visits_day_dimension_key", table_name="site_visits")


def downgrade() -> None:
    op.create_index(
        "ix_site_visits_day_dimension_key",
        "site_visits",
        ["day", "dimension", "key"],
        unique=True,
    )
    op.drop_index("ix_site_visits_dimension_day_key", table_name="site_visits")
