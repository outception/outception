"""drop notifications

Revision ID: 1c9a113526da
Revises: 53cc9492a52a
Create Date: 2026-06-22 22:47:17.426923

"""

from alembic import op

# Outception Custom Imports

# revision identifiers, used by Alembic.
revision = "1c9a113526da"
down_revision = "53cc9492a52a"
branch_labels: tuple[str] | None = None
depends_on: tuple[str] | None = None


def upgrade() -> None:
    # Ensures we don't break app by applying a deadlock-inducing migration
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.execute(
        "DROP TABLE IF EXISTS notifications, user_notifications, "
        "notification_recipients CASCADE"
    )


def downgrade() -> None:
    # Ensures we don't break app by applying a deadlock-inducing migration
    op.execute("SET LOCAL lock_timeout = '5s'")
    # The notifications feature was removed; this drop is irreversible.
    pass
