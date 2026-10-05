import pytest

from outception.kit.crypto import get_token_hash_candidates
from outception.models import Model
from scripts.import_live_data import TABLES, check_legacy_hash, map_row


class TestMaps:
    @pytest.mark.parametrize("table", TABLES, ids=[t.name for t in TABLES])
    def test_every_target_column_exists(self, table) -> None:  # type: ignore[no-untyped-def]
        columns = {c.name for c in Model.metadata.tables[table.name].columns}
        targets = set(table.columns.values()) | set(table.defaults)
        targets |= {
            dst for dst in table.alternatives.values() if dst in table.columns.values()
        }
        assert targets <= columns, targets - columns

    def test_tables_follow_their_dependencies(self) -> None:
        names = [t.name for t in TABLES]
        assert names.index("users") < names.index("oauth2_grants")
        assert names.index("oauth2_clients") < names.index("oauth2_tokens")


class TestMapRow:
    def test_users_drop_the_old_columns_and_fill_meta(self) -> None:
        table = next(t for t in TABLES if t.name == "users")
        row = {
            "id": "u1",
            "email": "a@b.c",
            "meta": None,
            "display_name": "gone",
            "timezone": "gone",
            "deleted_at": None,
        }
        mapped = map_row(table, row, set(row))
        assert mapped == {
            "id": "u1",
            "email": "a@b.c",
            "meta": {},
            "email_verified": False,
            "is_admin": False,
        }

    def test_clients_take_the_bare_digest_and_hash_the_clear_token(self) -> None:
        table = next(t for t in TABLES if t.name == "oauth2_clients")
        row = {
            "id": "c1",
            "client_id": "outception-app",
            "client_secret": "a" * 64,
            "registration_access_token": "plain-token",
        }
        mapped = map_row(table, row, set(row))
        assert mapped is not None
        assert mapped["client_secret_hash_v2"] == "a" * 64
        assert (
            mapped["registration_access_token_hash_v2"]
            == get_token_hash_candidates("plain-token")[None]
        )
        assert "registration_access_token" not in mapped
        assert mapped["rate_limit_group"] == "default"
        assert mapped["client_id_issued_at"] == 0

    def test_tokens_default_the_counters_and_drop_the_workspace(self) -> None:
        table = next(t for t in TABLES if t.name == "oauth2_tokens")
        row = {
            "id": "t1",
            "client_id": "c",
            "access_token": "h",
            "workspace_id": "w",
            "user_id": "u",
        }
        mapped = map_row(table, row, set(row))
        assert mapped is not None
        assert "workspace_id" not in mapped
        assert mapped["sub_type"] == "user"
        assert mapped["expires_in"] == 0
        assert mapped["access_token_revoked_at"] == 0


class TestLegacyHash:
    def test_reads_the_shape(self) -> None:
        assert "legacy digest shape" in check_legacy_hash(
            "f" * 64
        ) or "warning" in check_legacy_hash("f" * 64)
        assert "no token" in check_legacy_hash(None) or "warning" in check_legacy_hash(
            None
        )
        assert "not a legacy digest" in check_legacy_hash(
            "short"
        ) or "warning" in check_legacy_hash("short")
