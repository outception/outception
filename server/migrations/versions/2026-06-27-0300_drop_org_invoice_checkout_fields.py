"""drop dead MoR organization invoice/checkout/onboarding columns

Revision ID: d0f4a2c6b3e8
Revises: c9e3f1a5b2d7
Create Date: 2026-06-27 03:00:00.000000

"""

from alembic import op

# Outception Custom Imports

# revision identifiers, used by Alembic.
revision = "d0f4a2c6b3e8"
down_revision = "c9e3f1a5b2d7"
branch_labels: tuple[str] | None = None
depends_on: tuple[str] | None = None

_COLUMNS = [
    "customer_invoice_prefix",
    "customer_invoice_next_number",
    "checkout_settings",
    "details_submitted_at",
]


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    for column in _COLUMNS:
        op.execute(f"ALTER TABLE organizations DROP COLUMN IF EXISTS {column}")


def downgrade() -> None:
    # Dead MoR invoice/checkout/onboarding fields removed; irreversible.
    pass
