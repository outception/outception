"""Import the live tree's readers into the rebuilt schema.

    python -m scripts.import_live_data --source postgresql://... [--target postgresql://...] [--commit]

Reads the live database and writes the rebuilt one with explicit column
maps, table by table, in dependency order. Without `--commit` it is a dry
run: it reports what every table would carry, what it would skip and why,
and checks a sampled token hash against the legacy hash path. The source
connection is read-only; the import never writes to the live database.

The target defaults to the rebuilt server's own settings. `OUTCEPTION_SECRET`
must be the live tree's: the live tree's bare token digests validate only
through the legacy candidate path under the same secret.
"""

import argparse
import json
import sys
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any

import psycopg2
import psycopg2.extras

from outception.config import settings
from outception.kit.crypto import get_legacy_secret, get_token_hash_candidates

BATCH = 500


@dataclass(frozen=True)
class TableMap:
    """How one live table lands in the rebuilt one."""

    name: str
    # Live column -> rebuilt column. Columns the live table has and this map
    # leaves out are dropped on purpose.
    columns: dict[str, str]
    # Rebuilt columns filled when the live row has nothing for them.
    defaults: dict[str, Any] = field(default_factory=dict)
    # Older live columns that stand in for a mapped one when present.
    alternatives: dict[str, str] = field(default_factory=dict)
    # A per-row hook for what a map cannot say.
    transform: Callable[[dict[str, Any]], dict[str, Any] | None] | None = None
    # Live columns the row cannot do without; the table is skipped when the
    # live schema lacks them.
    requires: tuple[str, ...] = ()


RECORD = {
    "id": "id",
    "created_at": "created_at",
    "modified_at": "modified_at",
    "deleted_at": "deleted_at",
}


def _hash_registration_token(row: dict[str, Any]) -> dict[str, Any] | None:
    """A live client may hold its registration token in clear; the rebuilt
    schema keeps a hash, computed with the legacy secret so the live value
    keeps validating."""
    plain = row.pop("registration_access_token", None)
    if plain and not row.get("registration_access_token_hash_v2"):
        row["registration_access_token_hash_v2"] = get_token_hash_candidates(plain)[
            None
        ]
    return row


TABLES: tuple[TableMap, ...] = (
    TableMap(
        "users",
        {
            **RECORD,
            "email": "email",
            "email_verified": "email_verified",
            "is_admin": "is_admin",
            "avatar_url": "avatar_url",
            "accepted_terms_of_service_at": "accepted_terms_of_service_at",
            "accepted_terms_of_service_ip": "accepted_terms_of_service_ip",
            "blocked_at": "blocked_at",
            "meta": "meta",
            "first_name": "first_name",
            "last_name": "last_name",
        },
        defaults={"meta": {}, "email_verified": False, "is_admin": False},
        requires=("email",),
    ),
    TableMap(
        "oauth_accounts",
        {
            **RECORD,
            "platform": "platform",
            "access_token": "access_token",
            "access_token_encrypted": "access_token_encrypted",
            "expires_at": "expires_at",
            "refresh_token": "refresh_token",
            "refresh_token_encrypted": "refresh_token_encrypted",
            "refresh_token_expires_at": "refresh_token_expires_at",
            "account_id": "account_id",
            "account_email": "account_email",
            "account_username": "account_username",
            "user_id": "user_id",
        },
        # Without the encrypted copy a social login cannot be carried; the
        # reader signs in again and the row is recreated.
        requires=("access_token_encrypted",),
    ),
    TableMap(
        "oauth2_clients",
        {
            **RECORD,
            "client_id": "client_id",
            "client_secret_hash_v2": "client_secret_hash_v2",
            "client_secret_encrypted": "client_secret_encrypted",
            "registration_access_token_hash_v2": "registration_access_token_hash_v2",
            "registration_access_token_encrypted": "registration_access_token_encrypted",
            "first_party": "first_party",
            "user_id": "user_id",
            "rate_limit_group": "rate_limit_group",
            "client_id_issued_at": "client_id_issued_at",
            "client_secret_expires_at": "client_secret_expires_at",
            "client_metadata": "client_metadata",
        },
        defaults={
            "first_party": False,
            "rate_limit_group": "default",
            "client_id_issued_at": 0,
            "client_secret_expires_at": 0,
        },
        alternatives={
            # The live tree's bare digest validates through the legacy path.
            "client_secret": "client_secret_hash_v2",
            "registration_access_token": "registration_access_token",
        },
        transform=_hash_registration_token,
    ),
    TableMap(
        "oauth2_grants",
        {**RECORD, "client_id": "client_id", "scope": "scope", "user_id": "user_id"},
        defaults={"scope": ""},
    ),
    TableMap(
        "oauth2_tokens",
        {
            **RECORD,
            "client_id": "client_id",
            "nonce": "nonce",
            "token_type": "token_type",
            "access_token": "access_token",
            "refresh_token": "refresh_token",
            "scope": "scope",
            "issued_at": "issued_at",
            "access_token_revoked_at": "access_token_revoked_at",
            "refresh_token_revoked_at": "refresh_token_revoked_at",
            "expires_in": "expires_in",
            "sub_type": "sub_type",
            "user_id": "user_id",
        },
        defaults={
            "issued_at": 0,
            "access_token_revoked_at": 0,
            "refresh_token_revoked_at": 0,
            "expires_in": 0,
            "sub_type": "user",
            "token_type": "bearer",
        },
    ),
    TableMap(
        "totp_enrollments",
        {
            **RECORD,
            "enabled": "enabled",
            "secret": "secret",
            "algorithm": "algorithm",
            "code_length": "code_length",
            "time_step": "time_step",
            "last_verified_time_step": "last_verified_time_step",
            "identity_id": "identity_id",
        },
    ),
    TableMap(
        "backup_codes_enrollments",
        {
            **RECORD,
            "codes_hashes": "codes_hashes",
            "used_codes_hashes": "used_codes_hashes",
            "identity_id": "identity_id",
        },
        defaults={"codes_hashes": [], "used_codes_hashes": []},
    ),
    TableMap(
        "user_followed_sources",
        {**RECORD, "user_id": "user_id", "source_id": "source_id"},
    ),
)


def map_row(
    table: TableMap, row: dict[str, Any], live_columns: set[str]
) -> dict[str, Any] | None:
    """One live row in the rebuilt shape, or None when it cannot be carried."""
    out: dict[str, Any] = {}
    for src, dst in table.columns.items():
        if src in live_columns and row.get(src) is not None:
            out[dst] = row[src]
    for src, dst in table.alternatives.items():
        if src in live_columns and row.get(src) is not None and dst not in out:
            out[dst] = row[src]
    for dst, value in table.defaults.items():
        if out.get(dst) is None:
            out[dst] = value
    if table.transform is not None:
        return table.transform(out)
    return out


def live_columns_of(cursor: Any, table: str) -> set[str]:
    cursor.execute(
        "select column_name from information_schema.columns where table_name = %s",
        (table,),
    )
    return {name for (name,) in cursor.fetchall()}


def live_rows(cursor: Any, table: str) -> Iterator[dict[str, Any]]:
    cursor.itersize = BATCH
    cursor.execute(f'select * from "{table}" where deleted_at is null')
    for row in cursor:
        yield dict(row)


def _encode(value: Any) -> Any:
    if isinstance(value, dict | list):
        return psycopg2.extras.Json(value)
    return value


def insert_rows(cursor: Any, table: str, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    columns = sorted({key for row in rows for key in row})
    template = "(" + ",".join(["%s"] * len(columns)) + ")"
    values = [tuple(_encode(row.get(c)) for c in columns) for row in rows]
    quoted = ",".join(f'"{c}"' for c in columns)
    psycopg2.extras.execute_values(
        cursor,
        f'insert into "{table}" ({quoted}) values %s on conflict (id) do nothing',
        values,
        template=template,
        page_size=BATCH,
    )
    return cursor.rowcount if cursor.rowcount >= 0 else len(rows)


def check_legacy_hash(sample: str | None) -> str:
    """A stored live token must look like the legacy digest the rebuilt
    lookup still tries first: 64 hex characters under the same secret."""
    secret = get_legacy_secret()
    if not secret or secret == "super secret jwt-secret-key":
        return "warning: OUTCEPTION_SECRET is unset or the development default"
    if sample is None:
        return "no token to sample"
    if len(sample) == 64 and all(c in "0123456789abcdef" for c in sample):
        return "sampled token hash has the legacy digest shape"
    return (
        f"warning: sampled token hash is {len(sample)} characters, not a legacy digest"
    )


def run(source_dsn: str, target_dsn: str, commit: bool) -> dict[str, Any]:
    report: dict[str, Any] = {"mode": "commit" if commit else "dry-run", "tables": {}}
    source = psycopg2.connect(source_dsn)
    source.set_session(readonly=True, autocommit=False)
    target = psycopg2.connect(target_dsn) if commit else None
    try:
        sample_hash: str | None = None
        for table in TABLES:
            with source.cursor() as probe:
                columns = live_columns_of(probe, table.name)
            entry: dict[str, Any] = {"live_rows": 0, "carried": 0, "skipped": 0}
            report["tables"][table.name] = entry
            if not columns:
                entry["note"] = "not in the live schema"
                continue
            missing = [c for c in table.requires if c not in columns]
            if missing:
                entry["note"] = f"skipped: the live schema lacks {', '.join(missing)}"
                continue
            dropped = sorted(columns - set(table.columns) - set(table.alternatives))
            if dropped:
                entry["dropped_columns"] = dropped
            batch: list[dict[str, Any]] = []
            with source.cursor(
                name=f"import_{table.name}",
                cursor_factory=psycopg2.extras.RealDictCursor,
            ) as rows:
                for row in live_rows(rows, table.name):
                    entry["live_rows"] += 1
                    mapped = map_row(table, row, columns)
                    if mapped is None:
                        entry["skipped"] += 1
                        continue
                    if table.name == "oauth2_tokens" and sample_hash is None:
                        sample_hash = mapped.get("access_token")
                    entry["carried"] += 1
                    if target is not None:
                        batch.append(mapped)
                        if len(batch) >= BATCH:
                            with target.cursor() as writer:
                                insert_rows(writer, table.name, batch)
                            batch = []
            if target is not None and batch:
                with target.cursor() as writer:
                    insert_rows(writer, table.name, batch)
        report["legacy_hash"] = check_legacy_hash(sample_hash)
        if target is not None:
            target.commit()
    finally:
        source.rollback()
        source.close()
        if target is not None:
            target.close()
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--source", required=True, help="the live database DSN (read only)"
    )
    parser.add_argument(
        "--target",
        default=settings.get_postgres_dsn("psycopg2"),
        help="the rebuilt database DSN (defaults to the settings)",
    )
    parser.add_argument(
        "--commit", action="store_true", help="write; the default is a dry run"
    )
    args = parser.parse_args(argv)
    report = run(args.source, args.target, args.commit)
    print(json.dumps(report, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
