"""drop feedbacks

Revision ID: 53cc9492a52a
Revises: b7d59566274a
Create Date: 2026-06-22 22:24:41.460460

"""

from alembic import op

# Polar Custom Imports

# revision identifiers, used by Alembic.
revision = "53cc9492a52a"
down_revision = "b7d59566274a"
branch_labels: tuple[str] | None = None
depends_on: tuple[str] | None = None


def upgrade() -> None:
    # Ensures we don't break app by applying a deadlock-inducing migration
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.execute("DROP TABLE IF EXISTS feedbacks CASCADE")


def downgrade() -> None:
    # Ensures we don't break app by applying a deadlock-inducing migration
    op.execute("SET LOCAL lock_timeout = '5s'")
    # The feedbacks feature was removed; this drop is irreversible.
    pass
