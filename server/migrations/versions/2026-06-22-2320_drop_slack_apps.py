"""drop slack_apps

Revision ID: f92ebdfbe7b0
Revises: 1c9a113526da
Create Date: 2026-06-22 23:20:46.163394

"""

from alembic import op

# Polar Custom Imports

# revision identifiers, used by Alembic.
revision = "f92ebdfbe7b0"
down_revision = "1c9a113526da"
branch_labels: tuple[str] | None = None
depends_on: tuple[str] | None = None


def upgrade() -> None:
    # Ensures we don't break app by applying a deadlock-inducing migration
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.execute("DROP TABLE IF EXISTS slack_apps CASCADE")


def downgrade() -> None:
    # Ensures we don't break app by applying a deadlock-inducing migration
    op.execute("SET LOCAL lock_timeout = '5s'")
    # The Slack integration was removed; this drop is irreversible.
    pass
