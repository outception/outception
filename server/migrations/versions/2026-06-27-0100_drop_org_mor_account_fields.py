"""drop dead MoR organization account fields

Revision ID: b8d2e0f4a1c5
Revises: a7c1d9e3f2b4
Create Date: 2026-06-27 01:00:00.000000

"""

from alembic import op

# Outception Custom Imports

# revision identifiers, used by Alembic.
revision = "b8d2e0f4a1c5"
down_revision = "a7c1d9e3f2b4"
branch_labels: tuple[str] | None = None
depends_on: tuple[str] | None = None

_COLUMNS = ["support_tier", "total_balance", "internal_notes", "snooze_count"]


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    for column in _COLUMNS:
        op.execute(f"ALTER TABLE organizations DROP COLUMN IF EXISTS {column}")


def downgrade() -> None:
    # Dead MoR account fields removed from the product; drop is irreversible.
    pass
