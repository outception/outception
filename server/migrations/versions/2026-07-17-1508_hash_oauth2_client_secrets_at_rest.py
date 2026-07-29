"""hash oauth2 client secrets at rest

Revision ID: 9b7ace2a9be5
Revises: 2ea88d7cf991
Create Date: 2026-07-17 15:08:09.430409

"""

import re

import sqlalchemy as sa
from alembic import op

# Outception Custom Imports
from outception.config import settings
from outception.kit.crypto import get_token_hash

# revision identifiers, used by Alembic.
revision = "9b7ace2a9be5"
down_revision = "2ea88d7cf991"
branch_labels: tuple[str] | None = None
depends_on: tuple[str] | None = None

# An already-hashed secret is exactly 64 lowercase hex chars (HMAC-SHA256).
# Freshly generated plaintext secrets carry a prefix and mixed case, so this
# lets the migration be re-run safely without double-hashing.
_HASHED_RE = re.compile(r"^[0-9a-f]{64}$")


def upgrade() -> None:
    # Ensures we don't break app by applying a deadlock-inducing migration
    op.execute("SET LOCAL lock_timeout = '5s'")

    connection = op.get_bind()
    rows = connection.execute(
        sa.text("SELECT id, client_secret FROM oauth2_clients")
    ).fetchall()
    for row in rows:
        secret = row.client_secret
        if not secret or _HASHED_RE.match(secret):
            continue
        connection.execute(
            sa.text("UPDATE oauth2_clients SET client_secret = :hashed WHERE id = :id"),
            {"hashed": get_token_hash(secret, secret=settings.SECRET), "id": row.id},
        )


def downgrade() -> None:
    # Irreversible: plaintext client secrets cannot be recovered from their
    # HMAC-SHA256 hashes. Left as a no-op so the migration can still be
    # downgraded past without error.
    op.execute("SET LOCAL lock_timeout = '5s'")
