from pathlib import Path
from typing import Any, Literal

import pytest
from sqlalchemy.dialects.postgresql.asyncpg import PGDialect_asyncpg
from sqlalchemy.dialects.postgresql.psycopg2 import PGDialect_psycopg2
from sqlalchemy.engine import make_url

from outception.config import Environment, Settings, settings


def build_dsn(
    driver: Literal["asyncpg", "psycopg2"],
    *,
    fallback_host: str | None = "fallback.example.com",
    fallback_port: int | None = 5432,
) -> str:
    return settings._build_postgres_dsn(
        driver,
        username="outception",
        password="s3cret",
        host="primary.example.com",
        port=6432,
        database="outception",
        fallback_host=fallback_host,
        fallback_port=fallback_port,
    )


def get_connect_args(dsn: str) -> dict[str, Any]:
    url = make_url(dsn)
    dialect = (
        PGDialect_asyncpg()
        if url.drivername.endswith("asyncpg")
        else PGDialect_psycopg2()
    )
    _, connect_args = dialect.create_connect_args(url)
    return connect_args


class TestBuildPostgresDsn:
    def test_no_fallback(self) -> None:
        dsn = build_dsn("asyncpg", fallback_host=None, fallback_port=None)

        assert (
            dsn
            == "postgresql+asyncpg://outception:s3cret@primary.example.com:6432/outception"
        )

    @pytest.mark.parametrize(
        "password",
        ["abc/123XYZ", "p@ss/w0rd"],
    )
    @pytest.mark.parametrize("driver", ["asyncpg", "psycopg2"])
    def test_no_fallback_password_with_reserved_chars(
        self, driver: Literal["asyncpg", "psycopg2"], password: str
    ) -> None:
        dsn = settings._build_postgres_dsn(
            driver,
            username="outception",
            password=password,
            host="primary.example.com",
            port=6432,
            database="outception",
            fallback_host=None,
            fallback_port=None,
        )
        connect_args = get_connect_args(dsn)

        assert connect_args["password"] == password
        assert connect_args["host"] == "primary.example.com"
        database_key = "database" if driver == "asyncpg" else "dbname"
        assert connect_args[database_key] == "outception"

    def test_fallback_asyncpg(self) -> None:
        connect_args = get_connect_args(build_dsn("asyncpg"))

        assert connect_args["host"] == ["primary.example.com", "fallback.example.com"]
        assert connect_args["port"] == [6432, 5432]
        assert connect_args["password"] == "s3cret"

    def test_fallback_psycopg2(self) -> None:
        connect_args = get_connect_args(build_dsn("psycopg2"))

        assert connect_args["host"] == "primary.example.com,fallback.example.com"
        assert connect_args["port"] == "6432,5432"
        assert connect_args["password"] == "s3cret"

    def test_fallback_port_defaults_to_primary_port(self) -> None:
        connect_args = get_connect_args(build_dsn("asyncpg", fallback_port=None))

        assert connect_args["port"] == [6432, 6432]


class TestSigningKeySet:
    """A hosted environment must never sign with the development key set,
    which ships in the repository."""

    def test_production_refuses_the_development_set(self) -> None:
        from pydantic import ValidationError

        from outception.config import Settings

        with pytest.raises(ValidationError, match="development key set is public"):
            Settings(
                _env_file=None,
                ENV=Environment.production,
                ENCRYPTION_LOCAL_KEY="an operator key for the test",
                SECRET="a-strong-unique-value-" + "x" * 40,
            )

    def test_production_accepts_a_mounted_private_set(self, tmp_path: Path) -> None:
        from outception.config import Settings
        from outception.kit.jwk import generate_jwks

        key_file = tmp_path / "jwks.json"
        key_file.write_text(generate_jwks("outception_prod"))
        settings = Settings(
            _env_file=None,
            ENV=Environment.production,
            ENCRYPTION_LOCAL_KEY="an operator key for the test",
            SECRET="a-strong-unique-value-" + "x" * 40,
            LOCAL_JWKS=str(key_file),
            LOCAL_JWK_KID="outception_prod",
        )
        assert settings.LOCAL_JWK_KID == "outception_prod"

    def test_production_with_a_kms_key_needs_no_file(self) -> None:
        from outception.config import Settings

        settings = Settings(
            _env_file=None,
            ENV=Environment.production,
            ENCRYPTION_LOCAL_KEY="an operator key for the test",
            SECRET="a-strong-unique-value-" + "x" * 40,
            AWS_JWKS_KMS_KEY_ID="2f5a7b1c",
        )
        assert settings.AWS_JWKS_KMS_KEY_ID == "2f5a7b1c"


class TestAdminEmails:
    """The operator's variable on the host is a plain address, so the field
    takes a comma-separated list as well as a JSON list."""

    def test_plain_address(self) -> None:
        assert Settings.model_validate(
            {"ADMIN_EMAILS": "founder@outception.com"}
        ).ADMIN_EMAILS == ["founder@outception.com"]

    def test_comma_separated(self) -> None:
        settings = Settings.model_validate(
            {"ADMIN_EMAILS": " a@outception.com, b@outception.com ,"}
        )
        assert settings.ADMIN_EMAILS == ["a@outception.com", "b@outception.com"]

    def test_json_list(self) -> None:
        settings = Settings.model_validate({"ADMIN_EMAILS": '["a@outception.com"]'})
        assert settings.ADMIN_EMAILS == ["a@outception.com"]

    def test_from_environment(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OUTCEPTION_ADMIN_EMAILS", "founder@outception.com")
        assert Settings().ADMIN_EMAILS == ["founder@outception.com"]

    def test_empty(self) -> None:
        assert Settings.model_validate({"ADMIN_EMAILS": ""}).ADMIN_EMAILS == []


class TestEncryptionKey:
    def test_production_refuses_the_default_key(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="ships in the repository"):
            Settings(
                _env_file=None,
                ENV=Environment.production,
                SECRET="a-strong-unique-value-" + "x" * 40,
                AWS_JWKS_KMS_KEY_ID="2f5a7b1c",
            )

    def test_production_accepts_the_operator_key(self) -> None:
        settings = Settings(
            _env_file=None,
            ENV=Environment.production,
            SECRET="a-strong-unique-value-" + "x" * 40,
            AWS_JWKS_KMS_KEY_ID="2f5a7b1c",
            ENCRYPTION_LOCAL_KEY="an operator key for the test",
        )
        assert settings.ENCRYPTION_LOCAL_KEY == "an operator key for the test"

    def test_production_with_a_kms_key_needs_no_local_key(self) -> None:
        settings = Settings(
            _env_file=None,
            ENV=Environment.production,
            SECRET="a-strong-unique-value-" + "x" * 40,
            AWS_JWKS_KMS_KEY_ID="2f5a7b1c",
            AWS_KMS_KEY_ID="arn:kms:secrets",
        )
        assert settings.AWS_KMS_KEY_ID == "arn:kms:secrets"
