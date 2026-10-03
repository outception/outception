import base64
import json
import os
import tempfile
from datetime import timedelta
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import parse_qs, quote, unquote, urlparse

from annotated_types import Ge
from pydantic import AfterValidator, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

from outception.enums import EmailSender

# A token hash reads `<secret_id>$<digest>`. The digest is 64 characters
HASH_SEPARATOR = "$"
MAX_HASH_SECRET_ID_LENGTH = 15

DEVELOPMENT_JWKS = json.dumps(
    {
        "keys": [
            {
                "kty": "RSA",
                "kid": "outception_dev",
                "use": "sig",
                "n": "ru8ULeHoalP1LBFUiYo_055VtVqQgZCAGKxoiQNW8YdgBja1oclh0XOAPgG_AoITQOETDMlIxXV2ZBVzJ8DXMiZuyjTkCN5RSfXb3orgT7GOiLfm3GLLx_ft_3c3Lu942FMYQHV_cLh6iCIzsE6B2-RHth56LpXBc_ncwvqpXTq_misoISXqW9IH2MCL9A0WylWZQUwPJWb86dXUHc7-GCqNBTkFp0c8jyGFV3GCFuVucIWBjLx2_ceUfFn3c-F7vRyzSUzDlW22KMB7ylblN3oDkeJ1DB44fgqWGJBDyMU2LBZ95TZQeRcCUKlwpTCUORRF1fT4XzPkfCCxJ4epIQ",
                "e": "AQAB",
                "d": "BOk0T_zFaWVq_sOLyS1cO694aNYeiWyfk_xpwN2a-BPcrRVQcGF2wV-0jB5rbiwYU0bI90ptTxHMSDoBQ26apqSakUr-fds-kqIi0TK6jQeHNgJc_6Hhu6mTq7Yn5_A-xxU_cIvROekL6Od2O68F3pZK3GuASETZq0z_7BSyYtTCqGiDZF8sx0d5seCtd3C6fbGca_cFo-NP8v3hb6bnry8pdLWOxSwEI38WHJCMyznt51IhN1D1q78UZBeZRnWFq60Nt7XIKMpVN_07bYwvMYlkoCIL-0n5UNFVS_RegXzxHv-ymgz-hL8bfDvW2vDwLywZm_wwXl7LTeojyLLKuQ",
                "p": "3V29c8SlaiIJezymNrr9AYfThcgxYALlhCLgRzmPydPEtG99DP1zNfccWwJXZihlkDM1II4xMiabkFM0fZ8srFSrtH6mTLQIuVjVj-Lg-HUq9m33jKln0Jp80jy9odhQ_JIcylA3bCxlaFPF1WGL7nb62PhAawujT5snVLoOewU",
                "q": "yk2csW6gqxyBPffQ3SY0en9GtyoOPUgsemGj7gg22uzIRS5HjtArLci2TXfdgkGPXU_Wq4NO88LSe1YFfc_FjxK4pUNDnxUuEjf1BVoBkVWgQ93D-md-90gWS3us0HqzLAsT2KzqOCtZ-o1SHr0S_mB_TvA9R8sFBR1wgmm6qG0",
                "dp": "fPBUZku9xLozOcAQW-GLvNppcx97ZqIb4klA5lJBqnsAkYo_PR6rcPDoqyEWLQ1tzUZpnNdEQvbxZDLh9GjrcNRVGQlGWRJfviS6XHyD1xdiSTXluxk-A8m923b23KrXgsYAw9skfMRN8-UcSoPE07GJgP4UdZZa9Sovt61PUPU",
                "dq": "uD0ol_q9Pjhuh6X6RH13y5vAJi2Z3DuvriDgL3axpn2AAmkcaDazLDYfuLuSMv9L9lowkfC65YqnMAXuaF7hd-Q_3to8alPaqmLltWL8DITjuQrtYU4CNmgjTckrYI5uQI0yHOGVSWRJxMIRaMce1iXBq31lAc4mGzttbIeno50",
                "qi": "FRYsFSORwYOWN4mhQPegFjuuU5zba_LPfaKWX9o1gw3_ZlVr6pelgBhAbXD-SaU5PlkN3zceo-4h7relPRu_rgg5mvUkeqKCuRpzKNPWxJY62F6B8DDZeKLKD4fMrBPbr3Dx9i8zkyxPvaED3bHdIadOJnWcSaV63SWGrv7_6HE",
            }
        ]
    }
)


class Environment(StrEnum):
    development = "development"
    testing = "testing"  # Used for running tests
    sandbox = "sandbox"
    production = "production"


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
else:
    env_file = ".env"
file_extension = ".exe" if os.name == "nt" else ""

# The development default for ``SECRET``. It is fine locally but must never be
# used in a hosted environment: it keys all token hashing (OAuth codes, OTPs,
# sessions), so a known value means forgeable credentials. Enforced by
# ``_require_strong_secret`` below.
INSECURE_DEFAULT_SECRET = "super secret jwt secret"


class Settings(BaseSettings):
    ENV: Environment = Environment.development
    SQLALCHEMY_DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    TESTING: bool = False

    WORKER_HEALTH_CHECK_INTERVAL: timedelta = timedelta(seconds=30)
    WORKER_MAX_RETRIES: int = 20
    WORKER_MIN_BACKOFF_MILLISECONDS: int = 2_000
    # Misses in a row before the worker exits and gets restarted. Each miss
    # takes about 20s. Set to 0 to only log.
    WORKER_EVENT_LOOP_WATCHDOG_MAX_MISSES: int = 3
    WORKER_PROMETHEUS_DIR: Path = Path(tempfile.gettempdir()) / "prometheus_multiproc"

    # Prometheus remote write. Unset in production: the counters stay in the
    # process registry and are exposed on the internal network only.
    GRAFANA_CLOUD_PROMETHEUS_WRITE_URL: str | None = None
    GRAFANA_CLOUD_PROMETHEUS_WRITE_USERNAME: str | None = None
    GRAFANA_CLOUD_PROMETHEUS_WRITE_PASSWORD: str | None = None
    GRAFANA_CLOUD_PROMETHEUS_WRITE_INTERVAL: Annotated[int, Ge(1)] = 60  # seconds

    WORKER_DEFAULT_DEBOUNCE_MIN_THRESHOLD: timedelta = timedelta(seconds=15)
    WORKER_DEFAULT_DEBOUNCE_MAX_THRESHOLD: timedelta = timedelta(minutes=15)

    # Accounts (login, sessions, the OAuth2 provider, follows, server prefs).
    # When false none of those routers are mounted: the endpoints do not
    # exist, so they cannot be hit. Unset resolves per environment (see
    # `_default_accounts_enabled`): on in development and testing so the
    # suite keeps its auth coverage, off in the internet-facing environments
    # until the deploy sets it. Readers never need an account; submitting a
    # product to the daily card does.
    ACCOUNTS_ENABLED: bool | None = None

    # Emails allowed on the founder's review pages (Products of the day).
    ADMIN_EMAILS: list[str] = []

    SECRET: str = INSECURE_DEFAULT_SECRET
    HASH_SECRETS: dict[str, str] = {}
    CURRENT_HASH_SECRET_ID: str | None = None
    # The key set the LocalSigner signs with: a document, or a path to one.
    LOCAL_JWKS: str = DEVELOPMENT_JWKS
    LOCAL_JWK_KID: str = "outception_dev"
    WWW_AUTHENTICATE_REALM: str = "outception"

    # JSON list of accepted CORS origins
    CORS_ORIGINS: list[str] = []

    ALLOWED_HOSTS: set[str] = {"127.0.0.1:3000", "localhost:3000"}

    # Reverse proxies (by IP or CIDR) whose client-IP forwarding headers we
    # trust. A request's peer IP must fall inside one of these ranges before a
    # forwarding header is honoured; otherwise the header is ignored and the
    # socket peer IP is used. Leave empty to never trust forwarding headers
    # (correct when nothing sits in front of the app). In production set this
    # to the reverse proxy or CDN edge that terminates inbound requests.
    TRUSTED_PROXY_IPS: list[str] = []

    # Client-IP forwarding headers to honour (in priority order, first present
    # wins) when the peer is a trusted proxy. Set this to match whatever the
    # edge emits.
    TRUSTED_CLIENT_IP_HEADERS: list[str] = ["CF-Connecting-IP", "True-Client-IP"]

    # User-Agent sent by the outbound HTTP clients (feed fetches, reachability
    # checks). The field name is kept for parity with the live env file.
    OUTCEPTION_USER_AGENT: str = "Outception/1.0 (+https://outception.com)"

    # Base URL for the backend. Used by generate_external_url to
    # generate URLs to the backend accessible from the outside.
    BASE_URL: str = "http://127.0.0.1:8000"

    # URL to frontend app.
    FRONTEND_BASE_URL: str = "http://127.0.0.1:3000"
    FRONTEND_DEFAULT_RETURN_PATH: str = "/"

    # Authentication session
    AUTHENTICATION_SESSION_TTL: timedelta = timedelta(minutes=15)
    AUTHENTICATION_SESSION_COOKIE_KEY: str = "outception_auth_session"
    AUTHENTICATION_SESSION_COOKIE_DOMAIN: str | None = "127.0.0.1"

    # Email OTP
    EMAIL_OTP_TTL: timedelta = timedelta(minutes=30)
    EMAIL_OTP_CODE_LENGTH: int = 6

    # App Review bypass (for testing login flow during Apple/Google app reviews)
    APP_REVIEW_EMAIL: str | None = None
    APP_REVIEW_OTP_CODE: str | None = None

    # OAuth2 session state
    OAUTH2_SESSION_STATE_TTL: timedelta = timedelta(minutes=10)
    OAUTH2_SESSION_STATE_COOKIE_KEY: str = "outception_oauth2_state"
    OAUTH2_SESSION_STATE_COOKIE_DOMAIN: str | None = "127.0.0.1"

    # User session
    USER_SESSION_TTL: timedelta = timedelta(days=31)
    USER_SESSION_FRESHNESS_TTL: timedelta = timedelta(hours=1)
    USER_SESSION_COOKIE_KEY: str = "outception_session"
    USER_SESSION_COOKIE_DOMAIN: str | None = "127.0.0.1"

    # Email verification
    EMAIL_VERIFICATION_TTL_SECONDS: int = 60 * 30  # 30 minutes

    # Database
    POSTGRES_USER: str = "outception"
    POSTGRES_PWD: str = "outception"
    POSTGRES_HOST: str = "127.0.0.1"
    POSTGRES_PORT: int = 5432
    POSTGRES_HOST_FALLBACK: str | None = None
    POSTGRES_PORT_FALLBACK: int | None = None
    POSTGRES_DATABASE: str = "outception"
    POSTGRES_SSL: bool = False
    # Full connection URL, as injected by managed Postgres integrations.
    # When set, its components take precedence over the parts above.
    POSTGRES_URL_NON_POOLING: str | None = None
    DATABASE_POOL_SIZE: int = 5
    DATABASE_SYNC_POOL_SIZE: int = 1  # Specific pool size for sync connection: since we only use it in OAuth2 router, don't waste resources.
    DATABASE_POOL_RECYCLE_SECONDS: int = 600  # 10 minutes
    DATABASE_COMMAND_TIMEOUT_SECONDS: float = 30.0
    DATABASE_CONNECT_TIMEOUT_SECONDS: float = 10.0
    DATABASE_STREAM_YIELD_PER: int = 100

    POSTGRES_READ_USER: str | None = None
    POSTGRES_READ_PWD: str | None = None
    POSTGRES_READ_HOST: str | None = None
    POSTGRES_READ_PORT: int | None = None
    POSTGRES_READ_HOST_FALLBACK: str | None = None
    POSTGRES_READ_PORT_FALLBACK: int | None = None
    POSTGRES_READ_DATABASE: str | None = None

    # Redis
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    # Optional Redis AUTH. Redis is the job broker, the rate-limit store and
    # the card cache, so if it is ever reachable beyond a trusted network these
    # let an operator turn on authentication. Empty (default) means no auth.
    REDIS_USERNAME: str | None = None
    REDIS_PASSWORD: str | None = None
    # Full connection URL, for managed Redis requiring auth or TLS (rediss://),
    # which the parts above cannot express. Takes precedence when set.
    REDIS_URL: str | None = None

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
    # SMTP (used when EMAIL_SENDER=smtp). Production sends through SMTP:
    # host, port, STARTTLS, user = the sending address, password = an app
    # password of that account.
    EMAIL_SMTP_HOST: str = "smtp.gmail.com"
    EMAIL_SMTP_PORT: int = 587
    EMAIL_SMTP_USER: str = ""
    EMAIL_SMTP_PASSWORD: str = ""
    EMAIL_SMTP_STARTTLS: bool = True
    EMAIL_FROM_NAME: str = "Outception"
    EMAIL_FROM_DOMAIN: str = "outception.com"
    EMAIL_FROM_LOCAL: str = "no-reply"
    EMAIL_DEFAULT_REPLY_TO_NAME: str = "Outception Support"
    EMAIL_DEFAULT_REPLY_TO_EMAIL_ADDRESS: str = "support@outception.com"
    EMAIL_LOG_RETENTION_PERIOD: timedelta = timedelta(days=660)

    TURNSTILE_SECRET: str = ""

    # Google
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # Microsoft (common tenant, OpenID Connect)
    MICROSOFT_CLIENT_ID: str = ""
    MICROSOFT_CLIENT_SECRET: str = ""

    # Apple. APPLE_KEY_VALUE is the "Sign in with Apple" .p8 private key, used
    # to sign the ES256 client-secret JWT. See the validator below: CI ships
    # it base64-encoded because an env file cannot carry the key's newlines.
    APPLE_CLIENT_ID: str = ""
    APPLE_TEAM_ID: str = ""
    APPLE_KEY_ID: str = ""
    APPLE_KEY_VALUE: str = ""
    # Public token Apple hands you when configuring the Services ID domain;
    # served at /.well-known/apple-developer-domain-association.txt so Apple
    # can verify domain ownership before it accepts the Return URL.
    APPLE_DOMAIN_ASSOCIATION: str = ""

    @field_validator("APPLE_KEY_VALUE", mode="after")
    @classmethod
    def _normalize_apple_key(cls, value: str) -> str:
        """Resolve the Apple .p8 key to a real multi-line PEM. Accepts a raw
        PEM, a single-line PEM with escaped ``\\n`` newlines, or (the CI path)
        base64 of the .p8 file."""
        if not value:
            return value
        if "-----BEGIN" in value:
            return value.replace("\\n", "\n")
        try:
            decoded = base64.b64decode(value, validate=True).decode("utf-8")
        except ValueError, UnicodeDecodeError:
            return value
        return decoded if "-----BEGIN" in decoded else value

    # Summaries. The free lanes come first; the paid provider is the backup
    # for summaries only. No key set means summaries are disabled.
    GEMINI_API_KEY: str | None = None
    # One free-tier key per account, comma separated and tried in order. Falls
    # back to the single GEMINI_API_KEY above when unset.
    GEMINI_API_KEYS: str | None = None
    GEMINI_SUMMARY_MODEL: str = "gemini-3.5-flash-lite"
    # Free-tier calls per minute for summaries; headroom under the published
    # limit keeps a burst from tripping a cooldown.
    GEMINI_RPM_CAP: int = 12
    GROQ_API_KEY: str | None = None
    GROQ_API_KEYS: str | None = None
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    GROQ_RPM_CAP: int = 20
    MISTRAL_API_KEY: str | None = None
    MISTRAL_API_KEYS: str | None = None
    MISTRAL_MODEL: str = "ministral-8b-latest"
    MISTRAL_RPM_CAP: int = 30
    NVIDIA_API_KEY: str | None = None
    NVIDIA_API_KEYS: str | None = None
    NVIDIA_MODEL: str = "moonshotai/kimi-k3"
    NVIDIA_RPM_CAP: int = 30
    OLLAMA_API_KEY: str | None = None
    OLLAMA_API_KEYS: str | None = None
    OLLAMA_MODEL: str = "gpt-oss:120b"
    OLLAMA_RPM_CAP: int = 20
    CLOUDFLARE_ACCOUNT_ID: str | None = None
    CLOUDFLARE_AI_TOKEN: str | None = None
    CLOUDFLARE_AI_TOKENS: str | None = None
    CLOUDFLARE_MODEL: str = "@cf/openai/gpt-oss-120b"
    CLOUDFLARE_RPM_CAP: int = 20
    # Our own ceiling on requests per UTC day, well inside the free allowance,
    # so the account never reaches the point where a paid plan would bill.
    CLOUDFLARE_DAILY_CAP: int = 150
    ANTHROPIC_API_KEY: str | None = None
    SUMMARY_MODEL: str = "claude-haiku-4-5-20251001"
    # Global cost brake: summaries generated per UTC day across all readers
    # (cache hits do not count).
    SUMMARY_DAILY_CAP: int = 5000
    # Background summary warming per UTC day (free lanes only).
    SUMMARY_WARM_DAILY_CAP: int = 3500
    # Of that warm allowance, how much may go on speculative warming: articles
    # nobody has opened yet.
    SUMMARY_PRETAP_DAILY_CAP: int = 400
    # Resolve aggregator article links to the publisher URL before summarizing.
    GNEWS_RESOLVE_ENABLED: bool = True
    # When a publisher blocks the fetch or serves only a teaser, fetch the
    # article text through the reader fallback service instead.
    READER_FALLBACK_ENABLED: bool = True
    JINA_API_KEY: str | None = None
    # Table providers that need a free registration. Without a key the gated
    # tables are dropped from the roster; the keyless ones always serve.
    FINNHUB_API_KEY: str | None = None
    FOOTBALL_DATA_API_KEY: str | None = None
    CRICKETDATA_API_KEY: str | None = None
    # Company logo avatars for table tiles.
    LOGO_DEV_PUBLISHABLE_KEY: str | None = None

    # The model governor: every model call reserves against these caps and
    # settles afterwards. Two lanes, interactive (readers) and background
    # (warming, scoring, resolving), each with hourly and daily caps, a global
    # hourly cap and a daily cap on the paid lane. LLM_DISABLED is the kill
    # switch: summaries serve cached or teaser text and scoring pauses.
    LLM_DISABLED: bool = False
    LLM_INTERACTIVE_HOURLY_CAP: int = 600
    LLM_INTERACTIVE_DAILY_CAP: int = 5000
    LLM_BACKGROUND_HOURLY_CAP: int = 400
    LLM_BACKGROUND_DAILY_CAP: int = 5000
    LLM_GLOBAL_HOURLY_CAP: int = 900
    LLM_PAID_DAILY_CAP: int = 50
    LLM_BACKGROUND_SUBCAP_WARM: int = 3500
    LLM_BACKGROUND_SUBCAP_SCORE: int = 1000
    LLM_BACKGROUND_SUBCAP_RESOLVE: int = 500

    # The house decision model: a typed decision engine served from its own
    # container. Unset means every decision chain ends at the LLM rendering.
    ENGINE_URL: str | None = None
    ENGINE_API_KEY: str | None = None
    ENGINE_TIMEOUT_S: float = 2.0
    # Per-task provider order, comma separated; `llm_decider` is always last.
    DECISION_CHAIN_SCORE: str = "llm_decider"
    DECISION_CHAIN_CATEGORY: str = "llm_decider"
    DECISION_CHAIN_ROUTE: str = "llm_decider"
    DECISION_CHAIN_RESOLVE: str = "llm_decider"
    # Record the house model's answer beside the primary's without using it.
    DECISION_SHADOW: bool = False
    # An own generation endpoint, for whenever a generation model exists.
    OWN_GENERATION_URL: str | None = None
    OWN_GENERATION_MODEL: str | None = None
    OWN_GENERATION_API_KEY: str | None = None

    # Briefings
    BRIEFING_ENABLED: bool = False
    BRIEFING_PROFILES: list[str] = []
    BRIEFING_BUILD_CRON: str = "0 5 * * *"

    # Feedback digest and push notifications
    FEEDBACK_DIGEST_EMAIL: str | None = None
    WEB_PUSH_VAPID_PUBLIC_KEY: str | None = None
    WEB_PUSH_VAPID_PRIVATE_KEY: str | None = None
    WEB_PUSH_SUBJECT: str | None = None

    # Sentry
    SENTRY_DSN: str | None = None

    # Memory Profiling
    MEMORY_PROFILE_ENABLED: bool = False
    MEMORY_PROFILE_INTERVAL: int = 300  # seconds between snapshots
    MEMORY_PROFILE_S3_BUCKET_NAME: str | None = None

    # Logfire
    LOGFIRE_TOKEN: str | None = None
    LOGFIRE_IGNORED_ACTORS: set[str] = {
        # The task span records the whole message payload, and email.send's
        # props carry the live login code. Log stores must never hold live
        # credentials.
        "email.send",
    }
    # S3 logs storage
    S3_LOGS_BUCKET_NAME: str | None = None

    # AWS (logs and backups only)
    AWS_ACCESS_KEY_ID: str = "outception-development"
    AWS_SECRET_ACCESS_KEY: str = "outception123456789"
    AWS_REGION: str = "us-east-2"
    AWS_SIGNATURE_VERSION: str = "v4"
    # botocore defaults allow about 5 minutes per call. That is longer than the
    # job that started it, so a slow upload keeps a thread busy for nothing.
    AWS_S3_CONNECT_TIMEOUT_SECONDS: float = 5.0
    AWS_S3_READ_TIMEOUT_SECONDS: float = 20.0
    AWS_S3_MAX_ATTEMPTS: int = 3
    # Override to http://127.0.0.1:9000 in .env during development
    S3_ENDPOINT_URL: str | None = None
    # Endpoint used when generating presigned URLs handed to a browser.
    # Defaults to S3_ENDPOINT_URL.
    S3_PUBLIC_ENDPOINT_URL: str | None = None

    @property
    def s3_presign_endpoint_url(self) -> str | None:
        return self.S3_PUBLIC_ENDPOINT_URL or self.S3_ENDPOINT_URL

    # Secrets encryption. Production and sandbox wrap data keys with a KMS key
    # (AWS_KMS_KEY_ID); local and CI use a static key instead, so tests make no
    # cloud calls.
    AWS_KMS_KEY_ID: str | None = None
    ENCRYPTION_LOCAL_KEY: str = "super secret encryption key"

    # JWKS signing. Production and sandbox sign through a KMS asymmetric key
    # (AWS_JWKS_KMS_KEY_ID); elsewhere the key set in JWKS signs in process.
    AWS_JWKS_KMS_KEY_ID: str | None = None
    AWS_JWKS_KMS_PUBLISHED_KEY_IDS: list[str] = []

    # Token hashing. Unset, HASH_SECRETS and CURRENT_HASH_SECRET_ID are read
    # instead.
    AWS_HASH_SECRET_ARN: str | None = None

    # Application behaviours
    API_PAGINATION_MAX_LIMIT: int = 100
    API_MAX_REQUEST_BODY_SIZE: int = 10 * 1024 * 1024

    model_config = SettingsConfigDict(
        env_prefix="outception_",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_file=env_file,
        extra="allow",
    )

    @property
    def redis_url(self) -> str:
        if self.REDIS_URL:
            return self.REDIS_URL
        auth = ""
        if self.REDIS_PASSWORD:
            user = quote(self.REDIS_USERNAME or "", safe="")
            auth = f"{user}:{quote(self.REDIS_PASSWORD, safe='')}@"
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @model_validator(mode="after")
    def _default_accounts_enabled(self) -> "Settings":
        if self.ACCOUNTS_ENABLED is None:
            self.ACCOUNTS_ENABLED = self.ENV not in {
                Environment.production,
                Environment.sandbox,
            }
        return self

    @model_validator(mode="after")
    def _require_strong_secret(self) -> "Settings":
        # A hosted environment must never run with the development default
        # SECRET: it keys all token hashing, so a known value makes every
        # credential forgeable. Fail fast at startup rather than serve traffic.
        if (
            self.ENV in {Environment.production, Environment.sandbox}
            and self.SECRET == INSECURE_DEFAULT_SECRET
        ):
            raise ValueError(
                "OUTCEPTION_SECRET must be set to a strong, unique value in "
                f"{self.ENV}: it is still the insecure development default."
            )
        return self

    @model_validator(mode="after")
    def apply_postgres_url_non_pooling(self) -> "Settings":
        if self.POSTGRES_URL_NON_POOLING is None:
            return self

        url = urlparse(self.POSTGRES_URL_NON_POOLING)
        if url.scheme not in ("postgres", "postgresql"):
            raise ValueError(
                "POSTGRES_URL_NON_POOLING must be a postgres:// or postgresql:// URL"
            )

        if url.username:
            self.POSTGRES_USER = unquote(url.username)
        if url.password:
            self.POSTGRES_PWD = unquote(url.password)
        if url.hostname:
            self.POSTGRES_HOST = url.hostname
        if url.port:
            self.POSTGRES_PORT = url.port
        database = url.path.lstrip("/")
        if database:
            self.POSTGRES_DATABASE = database
        sslmode = parse_qs(url.query).get("sslmode", [None])[0]
        if sslmode is not None:
            self.POSTGRES_SSL = sslmode != "disable"
        return self

    @model_validator(mode="after")
    def check_hash_secrets(self) -> "Settings":
        for secret_id in self.HASH_SECRETS:
            if not 0 < len(secret_id) <= MAX_HASH_SECRET_ID_LENGTH:
                raise ValueError(
                    f"HASH_SECRETS id {secret_id!r} must be 1 to "
                    f"{MAX_HASH_SECRET_ID_LENGTH} characters"
                )
            if HASH_SEPARATOR in secret_id:
                raise ValueError(
                    f"HASH_SECRETS id {secret_id!r} must not contain {HASH_SEPARATOR!r}"
                )

        if (
            self.CURRENT_HASH_SECRET_ID is not None
            and self.CURRENT_HASH_SECRET_ID not in self.HASH_SECRETS
        ):
            raise ValueError(
                f"CURRENT_HASH_SECRET_ID {self.CURRENT_HASH_SECRET_ID!r} "
                "is not in HASH_SECRETS"
            )
        return self

    def _build_postgres_dsn(
        self,
        driver: Literal["asyncpg", "psycopg2"],
        *,
        username: str | None,
        password: str | None,
        host: str | None,
        port: int | None,
        database: str | None,
        fallback_host: str | None,
        fallback_port: int | None,
    ) -> str:
        if fallback_host is None:
            return URL.create(
                f"postgresql+{driver}",
                username=username,
                password=password,
                host=host,
                port=port,
                database=database,
            ).render_as_string(hide_password=False)
        return URL.create(
            f"postgresql+{driver}",
            username=username,
            password=password,
            database=database,
            query={
                "host": [
                    f"{host}:{port}",
                    f"{fallback_host}:{fallback_port or port}",
                ]
            },
        ).render_as_string(hide_password=False)

    def get_postgres_dsn(self, driver: Literal["asyncpg", "psycopg2"]) -> str:
        return self._build_postgres_dsn(
            driver,
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PWD,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            database=self.POSTGRES_DATABASE,
            fallback_host=self.POSTGRES_HOST_FALLBACK,
            fallback_port=self.POSTGRES_PORT_FALLBACK,
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

        return self._build_postgres_dsn(
            driver,
            username=self.POSTGRES_READ_USER,
            password=self.POSTGRES_READ_PWD,
            host=self.POSTGRES_READ_HOST,
            port=self.POSTGRES_READ_PORT,
            database=self.POSTGRES_READ_DATABASE,
            fallback_host=self.POSTGRES_READ_HOST_FALLBACK,
            fallback_port=self.POSTGRES_READ_PORT_FALLBACK,
        )

    def is_environment(self, environments: set[Environment]) -> bool:
        return self.ENV in environments

    def is_development(self) -> bool:
        return self.is_environment({Environment.development})

    def is_testing(self) -> bool:
        return self.is_environment({Environment.testing})

    def is_sandbox(self) -> bool:
        return self.is_environment({Environment.sandbox})

    def is_production(self) -> bool:
        return self.is_environment({Environment.production})

    def generate_external_url(self, path: str) -> str:
        return f"{self.BASE_URL}{path}"

    def generate_frontend_url(self, path: str) -> str:
        return f"{self.FRONTEND_BASE_URL}{path}"

    @property
    def frontend_hostname(self) -> str:
        return urlparse(self.FRONTEND_BASE_URL).hostname or "outception.com"


settings = Settings()
