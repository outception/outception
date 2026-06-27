"""drop MoR organization settings columns

Revision ID: a7c1d9e3f2b4
Revises: f1a2b3c4d5e6
Create Date: 2026-06-27 00:00:00.000000

"""

from alembic import op

# Outception Custom Imports

# revision identifiers, used by Alembic.
revision = "a7c1d9e3f2b4"
down_revision = "f1a2b3c4d5e6"
branch_labels: tuple[str] | None = None
depends_on: tuple[str] | None = None

_COLUMNS = [
    "subscription_settings",
    "order_settings",
    "customer_email_settings",
    "customer_portal_settings",
]


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    for column in _COLUMNS:
        op.execute(f"ALTER TABLE organizations DROP COLUMN IF EXISTS {column}")


def downgrade() -> None:
    # MoR subscription/order/customer-email/customer-portal settings were
    # removed from the product; this drop is irreversible.
    pass
