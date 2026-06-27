import functools
import os
import tempfile
from datetime import timedelta
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlparse

from annotated_types import Ge
from pydantic import (
    AfterValidator,
    Field,
    PostgresDsn,
    model_validator,
)
from pydantic_ai.models import Model, infer_model, parse_model_id
from pydantic_ai.providers.gateway import gateway_provider
from pydantic_settings import BaseSettings, SettingsConfigDict

from outception.enums import EmailSender
from outception.kit.jwk import JWKSFile


class Environment(StrEnum):
    development = "development"
    testing = "testing"  # Used for running tests
    sandbox = "sandbox"
    production = "production"
    test = "test"  # Used for the test environment in Render


def _validate_email_renderer_binary_path(value: Path) -> Path:
    if not value.exists() and not value.is_file():
        raise ValueError(
            f"""
        The provided email renderer binary path {value} is not a valid file path
        or does not exist.\n
        If you're in local development, you should build the email renderer binary
        by running the following command:\n
        uv run task emails\n
        """
        )

    return value


env = Environment(os.getenv("OUTCEPTION_ENV", Environment.development))
if env == Environment.testing:
    env_file = ".env.testing"
elif env == Environment.test:
    env_file = ".env.test"
else:
    env_file = ".env"
file_extension = ".exe" if os.name == "nt" else ""

# The development default for ``SECRET``. It is fine locally but must never be
# used in a hosted environment — it keys all token hashing (PATs, OAuth codes,
# OTPs, sessions), so a known value means forgeable credentials. Enforced by
# ``_require_strong_secret`` below.
INSECURE_DEFAULT_SECRET = "super secret jwt secret"


class Settings(BaseSettings):
    ENV: Environment = Environment.development
    SQLALCHEMY_DEBUG: bool = False
    POSTHOG_DEBUG: bool = False
    LOG_LEVEL: str = "DEBUG"
    TESTING: bool = False

    WORKER_HEALTH_CHECK_INTERVAL: timedelta = timedelta(seconds=30)
    WORKER_MAX_RETRIES: int = 20
    WORKER_MIN_BACKOFF_MILLISECONDS: int = 2_000
    WORKER_PROMETHEUS_DIR: Path = Path(tempfile.gettempdir()) / "prometheus_multiproc"

    # Grafana Cloud Prometheus
    GRAFANA_CLOUD_PROMETHEUS_WRITE_URL: str | None = None
    GRAFANA_CLOUD_PROMETHEUS_WRITE_USERNAME: str | None = None
    GRAFANA_CLOUD_PROMETHEUS_WRITE_PASSWORD: str | None = None
    GRAFANA_CLOUD_PROMETHEUS_WRITE_INTERVAL: Annotated[int, Ge(1)] = 60  # seconds
    GRAFANA_CLOUD_PROMETHEUS_QUERY_URL: str | None = None
    GRAFANA_CLOUD_PROMETHEUS_QUERY_USER: str | None = None
    GRAFANA_CLOUD_PROMETHEUS_QUERY_KEY: str | None = None

    # SLO Report
    SLO_REPORT_ENABLED: bool = True

    WEBHOOK_MAX_RETRIES: int = 10
    WEBHOOK_FIFO_GUARD_DELAY_MS: int = 300  # p95 is 236ms
    WEBHOOK_FIFO_GUARD_MAX_AGE: timedelta = timedelta(minutes=1)
    WEBHOOK_EVENT_RETENTION_PERIOD: timedelta = timedelta(days=90)
    WEBHOOK_FAILURE_THRESHOLD: int = 10

    WORKER_DEFAULT_DEBOUNCE_MIN_THRESHOLD: timedelta = timedelta(seconds=15)
    WORKER_DEFAULT_DEBOUNCE_MAX_THRESHOLD: timedelta = timedelta(minutes=15)

    SECRET: str = INSECURE_DEFAULT_SECRET
    JWKS: JWKSFile = Field(default="./.jwks.json")
    CURRENT_JWK_KID: str = "outception_dev"
    WWW_AUTHENTICATE_REALM: str = "outception"

    # JSON list of accepted CORS origins
    CORS_ORIGINS: list[str] = []

    ALLOWED_HOSTS: set[str] = {"127.0.0.1:3000", "localhost:3000"}

    # User-Agent sent by Outception's outbound HTTP clients (e.g. URL reachability
    # checks). Excludes the org review website/setup collectors, which use a
    # browser-like UA to avoid bot detection by CDNs.
    OUTCEPTION_USER_AGENT: str = "Outception/1.0 (+https://outception.com)"

    # Base URL for the backend. Used by generate_external_url to
    # generate URLs to the backend accessible from the outside.
    BASE_URL: str = "http://127.0.0.1:8000"

    # URL to frontend app.
    # Update to ngrok domain or similar in case you want
    # working Github badges in development.
    FRONTEND_BASE_URL: str = "http://127.0.0.1:3000"
    FRONTEND_DEFAULT_RETURN_PATH: str = "/"

    # Promotions: pay-to-post featured slots, charged through polar.sh as an
    # external payment gateway. A category's featured slot costs
    # PROMOTION_PRICE_CENTS per PROMOTION_BLOCK_MINUTES, buyable in multiples.
    # Empty PROMOTION_PRODUCT_ID disables checkout (the news wall still works).
    PROMOTION_PRODUCT_ID: str = ""
    PROMOTION_PRICE_CENTS: int = 1000  # $10 per block
    PROMOTION_BLOCK_MINUTES: int = 10
    # A viewer (IP + user-agent) counts at most one impression per promotion
    # within this window, so the news wall's background polling can't inflate
    # the count. 0 disables dedup.
    PROMOTION_IMPRESSION_DEDUP_SECONDS: int = 600
    # External payment gateway (polar.sh hosted checkout + Standard Webhooks).
    PAYMENT_GATEWAY_BASE_URL: str = "https://api.polar.sh"
    PAYMENT_GATEWAY_ACCESS_TOKEN: str = ""
    PAYMENT_GATEWAY_WEBHOOK_SECRET: str = ""

    # Authentication session
    AUTHENTICATION_SESSION_TTL: timedelta = timedelta(minutes=15)
    AUTHENTICATION_SESSION_COOKIE_KEY: str = "outception_auth_session"
    AUTHENTICATION_SESSION_COOKIE_DOMAIN: str = "127.0.0.1"

    # Email OTP
    EMAIL_OTP_TTL: timedelta = timedelta(minutes=30)
    EMAIL_OTP_CODE_LENGTH: int = 6

    # App Review bypass (for testing login flow during Apple/Google app reviews)
    APP_REVIEW_EMAIL: str | None = None
    APP_REVIEW_OTP_CODE: str | None = None

    # OAuth2 session state
    OAUTH2_SESSION_STATE_TTL: timedelta = timedelta(minutes=10)
    OAUTH2_SESSION_STATE_COOKIE_KEY: str = "outception_oauth2_state"
    OAUTH2_SESSION_STATE_COOKIE_DOMAIN: str = "127.0.0.1"

    # User session
    USER_SESSION_TTL: timedelta = timedelta(days=31)
    USER_SESSION_COOKIE_KEY: str = "outception_session"
    USER_SESSION_COOKIE_DOMAIN: str = "127.0.0.1"

    # Customer session

    # Impersonation session
    IMPERSONATION_COOKIE_KEY: str = "outception_original_session"
    IMPERSONATION_INDICATOR_COOKIE_KEY: str = "outception_is_impersonating"

    # Email verification
    EMAIL_VERIFICATION_TTL_SECONDS: int = 60 * 30  # 30 minutes

    # Database
    POSTGRES_USER: str = "outception"
    POSTGRES_PWD: str = "outception"
    POSTGRES_HOST: str = "127.0.0.1"
    POSTGRES_PORT: int = 5432
    POSTGRES_DATABASE: str = "outception"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_SYNC_POOL_SIZE: int = 1  # Specific pool size for sync connection: since we only use it in OAuth2 router, don't waste resources.
    DATABASE_POOL_RECYCLE_SECONDS: int = 600  # 10 minutes
    DATABASE_COMMAND_TIMEOUT_SECONDS: float = 30.0
    DATABASE_STREAM_YIELD_PER: int = 100

    POSTGRES_READ_USER: str | None = None
    POSTGRES_READ_PWD: str | None = None
    POSTGRES_READ_HOST: str | None = None
    POSTGRES_READ_PORT: int | None = None
    POSTGRES_READ_DATABASE: str | None = None

    # Redis
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # Emails
    EMAIL_RENDERER_BINARY_PATH: Annotated[
        Path, AfterValidator(_validate_email_renderer_binary_path)
    ] = (
        Path(__file__).parent.parent
        / "emails"
        / "bin"
        / f"react-email-pkg{file_extension}"
    )
    EMAIL_SENDER: EmailSender = EmailSender.logger
    RESEND_API_KEY: str = ""
    RESEND_API_BASE_URL: str = "https://api.resend.com"
    RESEND_WEBHOOK_SECRET: str = ""
    EMAIL_FROM_NAME: str = "Outception"
    EMAIL_FROM_DOMAIN: str = "notifications.outception.com"
    EMAIL_FROM_LOCAL: str = "mail"
    EMAIL_DEFAULT_REPLY_TO_NAME: str = "Outception Support"
    EMAIL_DEFAULT_REPLY_TO_EMAIL_ADDRESS: str = "support@outception.com"

    # Github App
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""

    # GitHub App for repository benefits
    GITHUB_REPOSITORY_BENEFITS_APP_IDENTIFIER: str = ""
    GITHUB_REPOSITORY_BENEFITS_APP_PRIVATE_KEY: str = ""
    GITHUB_REPOSITORY_BENEFITS_CLIENT_ID: str = ""
    GITHUB_REPOSITORY_BENEFITS_CLIENT_SECRET: str = ""

    # Google
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # Apple
    APPLE_CLIENT_ID: str = ""
    APPLE_TEAM_ID: str = ""
    APPLE_KEY_ID: str = ""
    APPLE_KEY_VALUE: str = ""

    # Pydantic AI Gateway
    PYDANTIC_AI_GATEWAY_API_KEY: str = "DummyKey"
    PYDANTIC_AI_GATEWAY_MODEL: str = "openai:gpt-5.5"

    # Organization review website scraping
    FIRECRAWL_API_KEY: str | None = None
    # Which scraper backs the JS-render path of the organization-review website
    # collector. "playwright" uses the in-house headless browser, "firecrawl"
    # uses Firecrawl Cloud, and "shadow" runs Firecrawl alongside Playwright to
    # log a comparison while still using Playwright's result for the live verdict.
    ORGANIZATION_REVIEW_SCRAPER: Literal["playwright", "firecrawl", "shadow"] = (
        "playwright"
    )

    # Stripe
    # Stripe webhook secrets
    STRIPE_STATEMENT_DESCRIPTOR: str = "OUTCEPTION"

    # Numeral
    NUMERAL_API_KEY: str | None = None

    # Sentry
    SENTRY_DSN: str | None = None

    # Posthog
    POSTHOG_PROJECT_API_KEY: str = ""

    # Tinybird
    TINYBIRD_API_URL: str = "http://localhost:7181"
    TINYBIRD_API_TOKEN: str | None = None
    TINYBIRD_READ_TOKEN: str | None = None
    TINYBIRD_CLICKHOUSE_URL: str = "http://localhost:7182"
    TINYBIRD_CLICKHOUSE_USERNAME: str = "default"
    TINYBIRD_CLICKHOUSE_TOKEN: str | None = None
    TINYBIRD_WORKSPACE: str | None = None
    TINYBIRD_BRANCH: str | None = None
    # Logo.dev (for company logo avatars)
    LOGO_DEV_PUBLISHABLE_KEY: str | None = None
    PERSONAL_EMAIL_DOMAINS: set[str] = {
        "gmail.com",
        "yahoo.com",
        "hotmail.com",
        "outlook.com",
        "aol.com",
        "icloud.com",
        "mail.com",
        "protonmail.com",
        "proton.me",
        "zoho.com",
        "gmx.com",
        "yandex.com",
        "msn.com",
        "live.com",
        "qq.com",
    }

    # Memory Profiling
    MEMORY_PROFILE_ENABLED: bool = False
    MEMORY_PROFILE_INTERVAL: int = 300  # seconds between snapshots
    MEMORY_PROFILE_S3_BUCKET_NAME: str | None = None

    # Logfire
    LOGFIRE_TOKEN: str | None = None
    LOGFIRE_IGNORED_ACTORS: set[str] = {
        "organization_access_token.record_usage",
        "personal_access_token.record_usage",
    }
    # S3 logs storage
    S3_LOGS_BUCKET_NAME: str | None = None

    # Plain
    PLAIN_CHAT_SECRET: str | None = None

    # AWS (File Downloads)
    AWS_ACCESS_KEY_ID: str = "outception-development"
    AWS_SECRET_ACCESS_KEY: str = "outception123456789"
    AWS_REGION: str = "us-east-2"
    AWS_SIGNATURE_VERSION: str = "v4"

    # Worker SQS/Lambda execution engine (POC)
    # When enabled, jobs enqueued for an allowlisted actor are routed to a
    # per-actor SQS queue (consumed by a Lambda) instead of the Redis broker.
    WORKER_SQS_ENABLED: bool = False
    WORKER_SQS_ACTORS: set[str] = {"dummy"}
    WORKER_SQS_QUEUE_PREFIX: str = "outception-tasks"
    # Override to http://127.0.0.1:4566 in .env to target LocalStack
    SQS_ENDPOINT_URL: str | None = None

    # Downloadable files
    S3_FILES_BUCKET_NAME: str = "outception-s3"
    S3_FILES_PUBLIC_BUCKET_NAME: str = "outception-s3-public"
    S3_FILES_PRESIGN_TTL: int = 3600  # 60 minutes
    S3_FILES_DOWNLOAD_SECRET: str = "supersecret"
    S3_FILES_DOWNLOAD_SALT: str = "saltysalty"
    # Override to http://127.0.0.1:9000 in .env during development
    S3_ENDPOINT_URL: str | None = None

    MINIO_USER: str = "outception"
    MINIO_PWD: str = "outceptionoutception"

    # Chargeback Stop
    CHARGEBACK_STOP_WEBHOOK_SECRET: str = ""

    # Outception's usage of Outception
    OUTCEPTION_ACCESS_TOKEN: str = ""
    OUTCEPTION_WEBHOOK_SECRET: str = ""
    OUTCEPTION_ORGANIZATION_ID: str = ""
    # Scale plan product, used by the Startup Program to grant a 100% discount
    OUTCEPTION_API_URL: str = "https://api.outception.com"

    # Customer portal URL overrides per organization

    # Invoices

    # Application behaviours
    API_PAGINATION_MAX_LIMIT: int = 100

    # Stripe enforces per-country minimum payout amounts in the recipient's
    # local currency. For most countries the per-currency minimum above
    # already exceeds the country minimum after FX conversion, but a few
    # don't fit that pattern: USD-denominated countries with a higher local
    # minimum than the default $10, and BSD (not listed per-currency above).
    # Values are in USD cents and indexed by ISO 3166-1 alpha-2 country
    # code, rounded up to the next multiple of $5 USD for FX headroom. See:
    # https://docs.stripe.com/global-payouts/send-money
    PLATFORM_FEE_BASIS_POINTS: int = 500
    PLATFORM_FEE_FIXED: int = 50
    PLATFORM_FEE_BASIS_POINTS_EARLY_ACCESS: int = 400
    PLATFORM_FEE_FIXED_EARLY_ACCESS: int = 40

    ORGANIZATION_BLOCKED_WORDS: list[str] = [
        "porn",
        "porno",
        "pornography",
        "sex",
        "sexual",
        "sexy",
        "nsfw",
        "xxx",
        "hentai",
        "erotic",
        "erotica",
        "fetish",
        "nude",
        "nudes",
        "nudity",
        "onlyfans",
        "camgirl",
        "escort",
    ]

    ORGANIZATION_SLUG_RESERVED_KEYWORDS: list[str] = [
        # Landing pages
        "benefits",
        "donations",
        "issue-funding",
        "newsletters",
        "products",
        "careers",
        "legal",
        # App
        "docs",
        "login",
        "signup",
        "oauth2",
        "checkout",
        "embed",
        "maintainer",
        "dashboard",
        "feed",
        "for-you",
        "posts",
        "purchases",
        "funding",
        "rewards",
        "settings",
        "backoffice",
        "maintainer",
        "finance",
        # Misc
        ".well-known",
    ]

    # Dunning Configuration
    DUNNING_RETRY_INTERVALS: list[timedelta] = [
        timedelta(days=2),  # First retry after 2 days
        timedelta(days=5),  # Second retry after 7 days (2 + 5)
        timedelta(days=7),  # Third retry after 14 days (2 + 5 + 7)
        timedelta(days=7),  # Fourth retry after 21 days (2 + 5 + 7 + 7)
    ]

    model_config = SettingsConfigDict(
        env_prefix="outception_",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_file=env_file,
        extra="allow",
    )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    def get_postgres_dsn(self, driver: Literal["asyncpg", "psycopg2"]) -> str:
        return str(
            PostgresDsn.build(
                scheme=f"postgresql+{driver}",
                username=self.POSTGRES_USER,
                password=self.POSTGRES_PWD,
                host=self.POSTGRES_HOST,
                port=self.POSTGRES_PORT,
                path=self.POSTGRES_DATABASE,
            )
        )

    def is_read_replica_configured(self) -> bool:
        return all(
            [
                self.POSTGRES_READ_USER,
                self.POSTGRES_READ_PWD,
                self.POSTGRES_READ_HOST,
                self.POSTGRES_READ_PORT,
                self.POSTGRES_READ_DATABASE,
            ]
        )

    def get_postgres_read_dsn(
        self, driver: Literal["asyncpg", "psycopg2"]
    ) -> str | None:
        if not self.is_read_replica_configured():
            return None

        return str(
            PostgresDsn.build(
                scheme=f"postgresql+{driver}",
                username=self.POSTGRES_READ_USER,
                password=self.POSTGRES_READ_PWD,
                host=self.POSTGRES_READ_HOST,
                port=self.POSTGRES_READ_PORT,
                path=self.POSTGRES_READ_DATABASE,
            )
        )

    @model_validator(mode="after")
    def _require_strong_secret(self) -> "Settings":
        # A hosted environment must never run with the development default
        # SECRET — it keys all token hashing, so a known value makes every
        # credential forgeable. Fail fast at startup rather than serve traffic.
        if (
            self.ENV in {Environment.production, Environment.sandbox}
            and self.SECRET == INSECURE_DEFAULT_SECRET
        ):
            raise ValueError(
                "OUTCEPTION_SECRET must be set to a strong, unique value in "
                f"{self.ENV} — it is still the insecure development default."
            )
        return self

    def is_environment(self, environments: set[Environment]) -> bool:
        return self.ENV in environments

    def is_development(self) -> bool:
        return self.is_environment({Environment.development})

    def is_testing(self) -> bool:
        return self.is_environment({Environment.testing})

    def is_sandbox(self) -> bool:
        return self.is_environment({Environment.sandbox, Environment.test})

    def is_production(self) -> bool:
        return self.is_environment({Environment.production})

    def is_tinybird_configured(self) -> bool:
        return bool(self.TINYBIRD_API_URL and self.TINYBIRD_API_TOKEN)

    def is_test(self) -> bool:
        return self.is_environment({Environment.test})

    def generate_external_url(self, path: str) -> str:
        return f"{self.BASE_URL}{path}"

    def generate_frontend_url(self, path: str) -> str:
        return f"{self.FRONTEND_BASE_URL}{path}"

    @property
    def frontend_hostname(self) -> str:
        return urlparse(self.FRONTEND_BASE_URL).hostname or "outception.com"

    @property
    def stripe_descriptor_suffix_max_length(self) -> int:
        return 22 - len("* ") - len(self.STRIPE_STATEMENT_DESCRIPTOR)

    def get_pydantic_gateway_model(
        self, model: str | None = None
    ) -> tuple[Model, str, str]:
        model = model or settings.PYDANTIC_AI_GATEWAY_MODEL
        model_provider, model_name = parse_model_id(model)
        assert model_provider is not None
        return (
            infer_model(
                model,
                provider_factory=functools.partial(
                    gateway_provider, api_key=self.PYDANTIC_AI_GATEWAY_API_KEY
                ),
            ),
            model_provider,
            model_name,
        )


settings = Settings()
