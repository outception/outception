"""widen oauth2 client_id/secret columns for outception_ prefix

Revision ID: f1a2b3c4d5e6
Revises: 0ed2b275d086
Create Date: 2026-06-26 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# Outception Custom Imports

# revision identifiers, used by Alembic.
revision = "f1a2b3c4d5e6"
down_revision = "0ed2b275d086"
branch_labels: tuple[str] | None = None
depends_on: tuple[str] | None = None

_COLUMNS = [
    ("oauth2_clients", "client_id"),
    ("oauth2_clients", "client_secret"),
    ("oauth2_authorization_codes", "client_id"),
    ("oauth2_grants", "client_id"),
    ("oauth2_tokens", "client_id"),
]


def upgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    for table, column in _COLUMNS:
        op.alter_column(
            table,
            column,
            existing_type=sa.String(length=52),
            type_=sa.String(length=64),
            existing_nullable=False,
        )


def downgrade() -> None:
    op.execute("SET LOCAL lock_timeout = '5s'")
    for table, column in _COLUMNS:
        op.alter_column(
            table,
            column,
            existing_type=sa.String(length=64),
            type_=sa.String(length=52),
            existing_nullable=False,
        )
