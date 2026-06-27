"""drop MoR organization review-subsystem columns

Revision ID: c9e3f1a5b2d7
Revises: b8d2e0f4a1c5
Create Date: 2026-06-27 02:00:00.000000

"""

from alembic import op

# Outception Custom Imports

# revision identifiers, used by Alembic.
revision = "c9e3f1a5b2d7"
down_revision = "b8d2e0f4a1c5"
branch_labels: tuple[str] | None = None
depends_on: tuple[str] | None = None

_COLUMNS = [
    "next_review_threshold",
    "status_updated_at",
    "initially_reviewed_at",
    "snoozed_until",
    "snooze_type",
]


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    # Dropping next_review_threshold also drops its CHECK constraint.
    for column in _COLUMNS:
        op.execute(f"ALTER TABLE organizations DROP COLUMN IF EXISTS {column}")


def downgrade() -> None:
    # Org review/approval subsystem removed from the product; irreversible.
    pass
