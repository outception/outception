"""client owner set null

Revision ID: 3f8a2c7d9e11
Revises: 7c1e5a9d2b40
Create Date: 2026-10-05 22:50:00.000000

"""

from alembic import op

# Outception Custom Imports

# revision identifiers, used by Alembic.
revision = "3f8a2c7d9e11"
down_revision = "7c1e5a9d2b40"
branch_labels: tuple[str] | None = None
depends_on: tuple[str] | None = None


def upgrade() -> None:
    # Ensures we don't break app by applying a deadlock-inducing migration.
    # CREATE INDEX CONCURRENTLY needs its own, far larger timeout -- see ADR-0006.
    op.execute("SET LOCAL lock_timeout = '5s'")
    # A reader's hard delete must not be stopped by a client they registered:
    # the client stays, unowned.
    op.drop_constraint(
        op.f("oauth2_clients_user_id_fkey"), "oauth2_clients", type_="foreignkey"
    )
    op.create_foreign_key(
        op.f("oauth2_clients_user_id_fkey"),
        "oauth2_clients",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("oauth2_clients_user_id_fkey"), "oauth2_clients", type_="foreignkey"
    )
    op.create_foreign_key(
        op.f("oauth2_clients_user_id_fkey"),
        "oauth2_clients",
        "users",
        ["user_id"],
        ["id"],
    )
