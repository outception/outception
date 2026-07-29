import base64
import os
import tempfile
from datetime import timedelta
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import quote, urlparse

from annotated_types import Ge
from pydantic import (
    AfterValidator,
    Field,
    PostgresDsn,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

from outception.enums import EmailSender
from outception.kit.jwk import JWKSFile


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
# used in a hosted environment - it keys all token hashing (PATs, OAuth codes,
# OTPs, sessions), so a known value means forgeable credentials. Enforced by
# ``_require_strong_secret`` below.
INSECURE_DEFAULT_SECRET = "super secret jwt secret"


class Settings(BaseSettings):
    ENV: Environment = Environment.development
    SQLALCHEMY_DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    TESTING: bool = False

    WORKER_MAX_RETRIES: int = 20
    WORKER_MIN_BACKOFF_MILLISECONDS: int = 2_000
    WORKER_PROMETHEUS_DIR: Path = Path(tempfile.gettempdir()) / "prometheus_multiproc"

    # Grafana Cloud Prometheus
    GRAFANA_CLOUD_PROMETHEUS_WRITE_URL: str | None = None
    GRAFANA_CLOUD_PROMETHEUS_WRITE_USERNAME: str | None = None
    GRAFANA_CLOUD_PROMETHEUS_WRITE_PASSWORD: str | None = None
    GRAFANA_CLOUD_PROMETHEUS_WRITE_INTERVAL: Annotated[int, Ge(1)] = 60  # seconds

    WORKER_DEFAULT_DEBOUNCE_MIN_THRESHOLD: timedelta = timedelta(seconds=15)
    WORKER_DEFAULT_DEBOUNCE_MAX_THRESHOLD: timedelta = timedelta(minutes=15)

    # Accounts (login, sessions, OAuth2 provider, orgs, tokens, email change)
    # are deactivated for the public launch. When false, none of those
    # routers are mounted - the endpoints don't exist, so they can't be hit.
    # Unset resolves per environment (see `_default_accounts_enabled`): on in
    # dev/test so the suite keeps its auth coverage, OFF in the internet-facing
    # environments. A missing env var must not silently expose the whole login,
    # OAuth2 and org surface in production.
    ACCOUNTS_ENABLED: bool | None = None

    SECRET: str = INSECURE_DEFAULT_SECRET
    JWKS: JWKSFile = Field(default="./.jwks.json")
    CURRENT_JWK_KID: str = "outception_dev"
    WWW_AUTHENTICATE_REALM: str = "outception"

    # JSON list of accepted CORS origins
    CORS_ORIGINS: list[str] = []

    ALLOWED_HOSTS: set[str] = {"127.0.0.1:3000", "localhost:3000"}

    # Reverse proxies (by IP or CIDR) whose client-IP forwarding headers we
    # trust. A request's peer IP must fall inside one of these ranges before a
    # forwarding header is honoured; otherwise the header is ignored and the
    # socket peer IP is used. Leave empty to NEVER trust forwarding headers
    # (correct when nothing sits in front of the app). In production set this to
    # the reverse proxy / CDN edge that terminates inbound requests (e.g. the
    # internal network of the Caddy/Cloudflare tier).
    TRUSTED_PROXY_IPS: list[str] = []

    # Client-IP forwarding headers to honour (in priority order, first present
    # wins) when the peer is a trusted proxy. Behind Cloudflare the real client
    # IP arrives in ``CF-Connecting-IP`` on ALL plans; ``True-Client-IP`` is
    # Cloudflare Enterprise-only. Set this to match whatever your edge emits.
    TRUSTED_CLIENT_IP_HEADERS: list[str] = ["CF-Connecting-IP", "True-Client-IP"]

    # User-Agent sent by Outception's outbound HTTP clients (e.g. URL reachability
    # checks). Excludes the org review website/setup collectors, which use a
    # browser-like UA to avoid bot detection by CDNs.
    OUTCEPTION_USER_AGENT: str = "Outception/1.0 (+https://outception.com)"

    # Base URL for the backend, accessible from the outside.
    BASE_URL: str = "http://127.0.0.1:8000"

    # URL to frontend app.
    FRONTEND_BASE_URL: str = "http://127.0.0.1:3000"
    FRONTEND_DEFAULT_RETURN_PATH: str = "/"

    # AI article summaries. Gemini's free tier is the primary provider; the
    # Anthropic API is the automatic paid backup when Gemini is out of quota or
    # erroring. Neither key set = summaries disabled (503).
    #
    # Anthropic spend is budgeted at $25/month (~$0.80/day). The *_PAID_* caps
    # below are daily ceilings on paid (Anthropic) calls sized so that even a
    # day with Gemini fully down stays inside that: summaries ~$0.01 each on
    # Haiku, translation batches ~$0.007 on Sonnet → 25 + 60 + 20 calls ≈ $0.81.
    GEMINI_API_KEY: str | None = None
    # One free-tier key per Google account, comma separated and tried in order:
    # each has its own per-minute and per-day quota, so a spent key fails over
    # to the next and the paid backup runs only when all are exhausted. Falls
    # back to the single GEMINI_API_KEY above when unset.
    GEMINI_API_KEYS: str | None = None
    GEMINI_SUMMARY_MODEL: str = "gemini-3.5-flash-lite"
    # Second line of FREE capacity (see news/free_llm.py): OpenAI-compatible
    # free tiers tried when Gemini is benched or spent, BEFORE any paid call.
    # Same single/comma-separated pattern as the Gemini keys. Unset = provider
    # not in the pool.
    GROQ_API_KEY: str | None = None
    GROQ_API_KEYS: str | None = None
    # gpt-oss-120b: the strongest model on Groq's free tier (1k requests/day),
    # solid multilingual; reasoning_effort is pinned low in free_llm._body so
    # it answers instead of thinking its token budget away.
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    # Free tier allows 30/min; headroom for the same reason as GEMINI_RPM_CAP.
    GROQ_RPM_CAP: int = 20
    MISTRAL_API_KEY: str | None = None
    MISTRAL_API_KEYS: str | None = None
    # ministral-8b, not mistral-small: the free plan's included allowance
    # serves the 8B ministral models but answers 429 (limit 0) for
    # small/medium - verified live 2026-09-05. Light, but this is the THIRD
    # free line; it only ever runs with Gemini and Groq both out, where the
    # alternative is a paid call, and the script/quality validators judge its
    # output like anyone else's.
    MISTRAL_MODEL: str = "ministral-8b-latest"
    # The free plan meters ~1 request/second; stay far under it.
    MISTRAL_RPM_CAP: int = 30
    CEREBRAS_API_KEY: str | None = None
    CEREBRAS_API_KEYS: str | None = None
    # Same gpt-oss-120b as Groq, served from Cerebras' free tier - a fourth
    # free line with its own quota pool, so one provider's daily reset never
    # decides whether the chain has capacity.
    CEREBRAS_MODEL: str = "gpt-oss-120b"
    # Free tier allows 30/min; headroom like the other free providers.
    CEREBRAS_RPM_CAP: int = 20
    ANTHROPIC_API_KEY: str | None = None
    SUMMARY_MODEL: str = "claude-haiku-4-5-20251001"
    # Global cost brake: LLM summaries generated per UTC day across all users
    # (cache hits don't count). Sized against the Gemini key fleet (9 keys ×
    # ~1k free requests/day, shared with translation): pre-tap warming raised
    # the warm share, and the total has to leave live taps at least as much
    # room as before.
    SUMMARY_DAILY_CAP: int = 5000
    # Paid (Haiku) summaries per UTC day once Gemini's free tier is spent. A
    # summary reads a whole article, ~$0.005 on Haiku, so 50 is about $0.25 on
    # a day that burns all of it - rebalanced against the translation warmer
    # below to keep the worst-case total inside the $25/month ceiling. Real
    # spend is far lower: Gemini serves free for most of most days.
    SUMMARY_PAID_DAILY_CAP: int = 50
    # Background hero-summary warming per UTC day (free Gemini tier only -
    # the warmer never calls the paid backup). Raised with pre-tap warming:
    # the roster sweep queues ~330 sources × 3 heroes as they churn, which sat
    # right at the old 900 - starving the viewed-card candidates the warmer
    # exists for. Two raises in two days (1,500 then 2,500) both filled while
    # the expanded roster backfilled; 3,500 clears the observed ceiling with
    # room for ordinary churn (~440 sources x 3 heroes as they rotate, plus
    # the 6-deep candidates from viewed cards). Worst case all of it lands on
    # the free fleet: 3,500 warm + the readers' share of the total cap sits
    # near half its ~10k/day capacity (9 Gemini keys + Groq + Mistral), and
    # the warmer never touches paid regardless.
    SUMMARY_WARM_DAILY_CAP: int = 3500
    # Resolve Google News article links to the publisher URL before summarizing
    # (unofficial Google endpoint - flip off if it starts failing or throttling;
    # those headlines then just open the article, as before).
    GNEWS_RESOLVE_ENABLED: bool = True
    # When a publisher blocks our fetch (bot wall, JS challenge) or serves only
    # a teaser, fetch the article text through the free Jina Reader service
    # instead. No key needed at low volume; a free key raises the rate limit.
    READER_FALLBACK_ENABLED: bool = True
    JINA_API_KEY: str | None = None
    # Headline translation runs on the same providers (Gemini free tier first,
    # Anthropic as the paid backup). Neither key set = headlines untranslated.
    # The cap counts PAID (Anthropic) calls per day - one call is up to 30
    # headlines, roughly $0.003 on Haiku, so 1000 caps the spend near $3/day.
    # Two independent budgets: readers get the full cap; the background warmer
    # gets a small allowance of its own (~$0.60/day) so pre-warming continues
    # when Gemini's free tier is spent without ever starving live readers.
    GEMINI_TRANSLATION_MODEL: str = "gemini-3.5-flash-lite"
    # Free-tier calls per minute shared by translations and summaries (the
    # tier allows 15; headroom keeps a burst from tripping a 429 that would
    # bench Gemini and push readers onto the paid path).
    GEMINI_RPM_CAP: int = 12
    # Haiku for the paid backup: about a third of Sonnet's price per token, and
    # the per-language script/variety hints in the prompt keep Croatian and
    # Serbian apart. Switch back to claude-sonnet-5 if mixing reappears.
    TRANSLATION_MODEL: str = "claude-haiku-4-5-20251001"
    # Paid (Haiku) batches live readers may spend per day once Gemini's free
    # tier is out: 250 batches of 15 headlines is about $0.40 on a day that
    # uses all of it. With the warmer's 150 and 25 paid summaries the worst
    # case (Gemini out all day) is ~$0.72/day, inside the $25/month ceiling;
    # a normal day is a fraction of that.
    TRANSLATION_PAID_DAILY_CAP: int = 250
    # The warmer's paid allowance only matters on days Gemini's free tier is
    # spent: 150 Haiku batches of 15 headlines is about $0.25, enough to keep
    # a reader's deck warm in the languages actually being read.
    # Trimmed from 150 to fund the higher paid-summary cap above without
    # raising the monthly total; only matters on days Gemini's free tier is
    # spent, and only for pre-warming (live readers keep their own 250).
    TRANSLATION_WARMER_PAID_DAILY_CAP: int = 110
    # The warmer's daily share of Gemini's FREE quota (batches). Without this
    # a cold morning warm run drains the free tier before any reader gets a
    # translation; the rest of the day's quota is reserved for live requests.
    TRANSLATION_WARMER_FREE_DAILY_CAP: int = 600
    # Stock-quote provider for the wall's market heatmap cards (finnhub.io free
    # tier). Without a key the stock heatmaps are dropped from the roster; the
    # keyless crypto heatmap (CoinGecko) is always available.
    FINNHUB_API_KEY: str | None = None
    # Soccer standings/results for the football heatmap cards
    # (football-data.org free tier, X-Auth-Token header). Without a key the
    # soccer heatmaps are dropped from the roster; the keyless sports maps
    # (ESPN big-4, F1) are always available.
    FOOTBALL_DATA_API_KEY: str | None = None
    # Live/recent cricket matches for the cricket heatmap card
    # (cricketdata.org "Lifetime Free" tier, 100 req/day - the 5-minute cache
    # window keeps usage at ~1/5min only while readers actually view the card).
    CRICKETDATA_API_KEY: str | None = None
    # Background cache-warmer: on a schedule, pre-translate the default-deck
    # headlines into these languages (comma-separated codes) so the first reader
    # in each doesn't wait on a cold translation. Empty disables the warmer.
    # Defaults to every non-English UI locale; only those readers asked for in
    # the last day are warmed, most-read first (see translate.note_demand).
    TRANSLATION_WARM_LANGUAGES: str = (
        "nl,fr,sv,es,de,hu,it,pt,pt-PT,ko,ja,tr,pl,ru,uk,ar,he,fa,hi,bn,ur,"
        "zh-Hans,zh-Hant,id,ms,tl,vi,th,cs,sk,sl,ro,bg,sr,sq,el,da,nb,fi,et,"
        "lv,lt,ga,ca,eu,hr"
    )

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
    DATABASE_CONNECT_TIMEOUT_SECONDS: float = 10.0
    DATABASE_STREAM_YIELD_PER: int = 100
    POSTGRES_SSL: bool = False

    POSTGRES_READ_USER: str | None = None
    POSTGRES_READ_PWD: str | None = None
    POSTGRES_READ_HOST: str | None = None
    POSTGRES_READ_PORT: int | None = None
    POSTGRES_READ_DATABASE: str | None = None

    # Redis
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    # Optional Redis AUTH. Redis is the Dramatiq broker + rate-limit + cache
    # backend, so if it's ever reachable beyond a trusted network these let an
    # operator turn on authentication. Empty (default) = no auth, as before.
    REDIS_USERNAME: str | None = None
    REDIS_PASSWORD: str | None = None

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
    # SMTP (used when EMAIL_SENDER=smtp; e.g. Gmail / Google Workspace).
    # Gmail: host smtp.gmail.com, port 587, STARTTLS on, user = the sending
    # address, password = a Google App Password (requires 2-Step Verification).
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

    # Microsoft (Azure AD / MSA - "common" tenant, OpenID Connect)
    MICROSOFT_CLIENT_ID: str = ""
    MICROSOFT_CLIENT_SECRET: str = ""

    # Google
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # Apple. APPLE_KEY_VALUE is the "Sign in with Apple" .p8 private key, used to
    # sign the ES256 client-secret JWT. See the validator below - CI ships it
    # base64-encoded because .env.prod can't carry the key's real newlines.
    APPLE_CLIENT_ID: str = ""
    APPLE_TEAM_ID: str = ""
    APPLE_KEY_ID: str = ""
    APPLE_KEY_VALUE: str = ""
    # Public token Apple hands you when configuring the Services ID domain;
    # served at /.well-known/apple-developer-domain-association.txt so Apple can
    # verify domain ownership before it accepts the Return URL.
    APPLE_DOMAIN_ASSOCIATION: str = ""

    @field_validator("APPLE_KEY_VALUE", mode="after")
    @classmethod
    def _normalize_apple_key(cls, value: str) -> str:
        """Resolve the Apple .p8 key to a real multi-line PEM. Accepts a raw
        PEM, a single-line PEM with escaped ``\\n`` newlines, or (the CI path)
        base64 of the .p8 file - the .env.prod pipeline can't carry literal
        newlines, so the deploy passes it base64-encoded."""
        if not value:
            return value
        if "-----BEGIN" in value:
            return value.replace("\\n", "\n")
        try:
            decoded = base64.b64decode(value, validate=True).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            return value
        return decoded if "-----BEGIN" in decoded else value

    # Sentry
    SENTRY_DSN: str | None = None

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
    WORKER_SQS_AWS_ACCESS_KEY_ID: str | None = None
    WORKER_SQS_AWS_SECRET_ACCESS_KEY: str | None = None
    WORKER_SQS_SCHEDULER_ROLE_ARN: str | None = None

    # API limits
    API_MAX_REQUEST_BODY_SIZE: int = 10 * 1024 * 1024

    # Override to http://127.0.0.1:4566 in .env to target LocalStack
    SQS_ENDPOINT_URL: str | None = None

    # Local S3 buckets provisioned by the dev docker bootstrap (see
    # dev/docker/scripts/startup.sh). Not read by application code today, but
    # kept so config, dev tooling, and env templates stay consistent.
    S3_FILES_BUCKET_NAME: str = "outception-s3"
    S3_FILES_PUBLIC_BUCKET_NAME: str = "outception-s3-public"
    # Override to http://127.0.0.1:9000 in .env during development
    S3_ENDPOINT_URL: str | None = None

    MINIO_USER: str = "outception"
    MINIO_PWD: str = "outceptionoutception"

    # Application behaviours
    API_PAGINATION_MAX_LIMIT: int = 100

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

    model_config = SettingsConfigDict(
        env_prefix="outception_",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_file=env_file,
        extra="allow",
    )

    @property
    def redis_url(self) -> str:
        auth = ""
        if self.REDIS_PASSWORD:
            user = quote(self.REDIS_USERNAME or "", safe="")
            auth = f"{user}:{quote(self.REDIS_PASSWORD, safe='')}@"
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

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
        # SECRET - it keys all token hashing, so a known value makes every
        # credential forgeable. Fail fast at startup rather than serve traffic.
        # Sandbox is internet-facing too, so it is held to the same bar.
        if (
            self.ENV in {Environment.production, Environment.sandbox}
            and self.SECRET == INSECURE_DEFAULT_SECRET
        ):
            raise ValueError(
                "OUTCEPTION_SECRET must be set to a strong, unique value in "
                f"{self.ENV} - it is still the insecure development default."
            )
        return self

    def is_environment(self, environments: set[Environment]) -> bool:
        return self.ENV in environments

    def is_development(self) -> bool:
        return self.is_environment({Environment.development})

    def is_testing(self) -> bool:
        return self.is_environment({Environment.testing})

    def is_production(self) -> bool:
        return self.is_environment({Environment.production})

    def is_sandbox(self) -> bool:
        return self.is_environment({Environment.sandbox})

    def is_tinybird_configured(self) -> bool:
        return bool(self.TINYBIRD_API_URL and self.TINYBIRD_API_TOKEN)

    def generate_frontend_url(self, path: str) -> str:
        return f"{self.FRONTEND_BASE_URL}{path}"

    @property
    def frontend_hostname(self) -> str:
        return urlparse(self.FRONTEND_BASE_URL).hostname or "outception.com"


settings = Settings()
