"""launch metrics indexes

Revision ID: c5e1a7d3f9b2
Revises: b4d8f2a6c1e7
Create Date: 2026-10-07 00:30:00.000000

"""

from alembic import op

# Outception Custom Imports

# revision identifiers, used by Alembic.
revision = "c5e1a7d3f9b2"
down_revision = "b4d8f2a6c1e7"
branch_labels: tuple[str] | None = None
depends_on: tuple[str] | None = None


def upgrade() -> None:
    # Ensures we don't break app by applying a deadlock-inducing migration.
    # CREATE INDEX CONCURRENTLY needs its own, far larger timeout -- see ADR-0006.
    op.execute("SET LOCAL lock_timeout = '5s'")
    # The two indexes every record table carries, which the first metrics
    # migration left out. Idempotent, so a host that already has them is fine.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_launch_metrics_created_at "
        "ON launch_metrics (created_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_launch_metrics_deleted_at "
        "ON launch_metrics (deleted_at)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_launch_metrics_deleted_at")
    op.execute("DROP INDEX IF EXISTS ix_launch_metrics_created_at")
