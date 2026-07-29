import hashlib
from collections.abc import Sequence
from functools import partial

import structlog
from fastapi.requests import Request
from fastapi.security.utils import get_authorization_scheme_param
from ratelimit import RateLimitMiddleware, Rule
from ratelimit.auths import EmptyInformation
from ratelimit.backends.redis import RedisBackend
from ratelimit.types import ASGIApp, Scope

from outception.config import Environment, settings
from outception.enums import RateLimitGroup
from outception.kit.http import get_ip_address
from outception.redis import Redis

log = structlog.get_logger()

_IDENTITY_KEY_PREFIX = "rl:ident:"
_IDENTITY_TTL_SECONDS = 300
_ANONYMOUS_IDENTITY = "anonymous"


def _bearer_token(scope: Scope) -> str | None:
    if scope.get("type") != "http":
        return None

    request = Request(scope)

    authorization = request.headers.get("authorization")
    if authorization is None:
        return None

    # Reject non-ASCII tokens outright: they can't be valid bearer tokens and
    # would otherwise yield a mojibake rate-limit key.
    if not authorization.isascii():
        return None

    scheme, token = get_authorization_scheme_param(authorization)
    if not scheme or scheme.lower() != "bearer" or not token:
        return None

    return token


def _session_cookie(scope: Scope) -> str | None:
    if scope.get("type") != "http":
        return None

    request = Request(scope)
    value = request.cookies.get(settings.USER_SESSION_COOKIE_KEY)
    return value or None


def _token_hash(token: str) -> str:
    return hashlib.blake2b(token.encode(), digest_size=16).hexdigest()


def _identity_cache_key(token: str) -> str:
    digest = hashlib.blake2b(token.encode(), digest_size=16).hexdigest()
    return f"{_IDENTITY_KEY_PREFIX}{digest}"


async def _read_cached_identity(
    redis: Redis, token: str
) -> tuple[str, RateLimitGroup] | None:
    raw = await redis.get(_identity_cache_key(token))
    if raw is None:
        return None
    group_str, sep, user = raw.partition("|")
    if not sep:
        return None
    try:
        return user, RateLimitGroup(group_str)
    except ValueError:
        return None


async def write_cached_identity(
    redis: Redis, token: str, key: tuple[str, RateLimitGroup]
) -> None:
    user, group = key
    await redis.set(
        _identity_cache_key(token),
        f"{group.value}|{user}",
        ex=_IDENTITY_TTL_SECONDS,
    )


async def clear_cached_identity(redis: Redis, token: str) -> None:
    await redis.delete(_identity_cache_key(token))


def _get_ip(scope: Scope) -> tuple[str, RateLimitGroup]:
    ip = get_ip_address(Request(scope))
    if ip is None:
        raise EmptyInformation(scope)
    return ip, RateLimitGroup.default


async def _authenticate(scope: Scope, *, redis: Redis) -> tuple[str, RateLimitGroup]:
    token = _bearer_token(scope)
    if token is not None:
        cached = await _read_cached_identity(redis, token)
        if cached is not None:
            return cached

    cookie = _session_cookie(scope)
    if cookie is not None:
        cached = await _read_cached_identity(redis, cookie)
        if cached is not None:
            return cached

    # A credential the auth layer has not vouched for (and the pre-login auth
    # session cookie) never earns a bucket of its own: a made-up value per
    # request would otherwise sidestep every limit while the request still
    # reaches the handler as anonymous. Such requests count against the
    # client's IP — in the endpoint's pending_auth twin when a credential was
    # presented.
    try:
        ip, group = _get_ip(scope)
    except (EmptyInformation, ValueError, TypeError):
        return _ANONYMOUS_IDENTITY, RateLimitGroup.default
    if token is not None or cookie is not None:
        return ip, RateLimitGroup.pending_auth
    return ip, group


# Each sensitive endpoint gets a `pending_auth` twin so requests with an
# unvalidated bearer token / cookie are counted in the endpoint's own zone
# instead of falling through to the catch-all `api` zone on `^/v1`.
_BASE_RULES: dict[str, Sequence[Rule]] = {
    "^/v1/login-code": [
        Rule(minute=6, hour=12, block_time=900, zone="login-code"),
        Rule(
            group=RateLimitGroup.pending_auth,
            minute=6,
            hour=12,
            block_time=900,
            zone="login-code",
        ),
    ],
    # /auth/start mints a fresh auth-session cookie, and the email-otp limit
    # below is keyed on that cookie — so without an IP cap here, an attacker
    # could mint unlimited cookies to reset the per-cookie budget and mailbomb
    # an address. Cap cookie minting per IP.
    "^/v1/auth/start": [
        Rule(minute=10, hour=100, block_time=300, zone="auth-start"),
        # Without the pending_auth twin, sending any garbage bearer token drops
        # the caller into that group, matches no rule here, and falls through to
        # the 60/min ^/v1 catch-all — 6x the cap this rule exists to impose.
        Rule(
            group=RateLimitGroup.pending_auth,
            minute=10,
            hour=100,
            block_time=300,
            zone="auth-start",
        ),
    ],
    "^/v1/auth/email-otp": [
        Rule(minute=6, hour=12, block_time=900, zone="auth-email-otp"),
        Rule(
            group=RateLimitGroup.pending_auth,
            minute=6,
            hour=12,
            block_time=900,
            zone="auth-email-otp",
        ),
    ],
    "^/v1/auth/totp": [
        Rule(minute=6, hour=12, block_time=900, zone="auth-totp"),
        Rule(
            group=RateLimitGroup.pending_auth,
            minute=6,
            hour=12,
            block_time=900,
            zone="auth-totp",
        ),
    ],
    "^/v1/auth/backup-codes": [
        Rule(minute=6, hour=12, block_time=900, zone="auth-backup-codes"),
        Rule(
            group=RateLimitGroup.pending_auth,
            minute=6,
            hour=12,
            block_time=900,
            zone="auth-backup-codes",
        ),
    ],
    "^/v1/email-update/(request|verify)": [
        Rule(minute=6, hour=12, block_time=900, zone="email-update"),
        Rule(
            group=RateLimitGroup.web,
            minute=6,
            hour=12,
            block_time=900,
            zone="email-update",
        ),
        Rule(
            group=RateLimitGroup.pending_auth,
            minute=6,
            hour=12,
            block_time=900,
            zone="email-update",
        ),
    ],
    # Public, unauthenticated upstream proxies (Open-Meteo / translation) plus
    # search, which fans out across the whole warm cache. Each distinct input is
    # a fresh upstream call + Redis key, so bound them tightly to stop
    # cache-cardinality abuse and getting our egress IP rate-limited.
    # /batch fans out across up to 256 sources per request, /{source_id} can
    # drive a live upstream fetch, and /heatmap/{id} proxies rate-capped quote
    # and sports providers — all belong in the tight zone rather than the
    # 500/min catch-all.
    # AI summaries call a model per cache miss, so one reader is bounded here;
    # the daily caps in summary.py bound the spend as a whole. The burst limit
    # sits above a reader tapping through a card, because a 429 on this route
    # sends the reader to the article instead. The hourly cap is a shape brake,
    # not the cost brake — the daily caps in summary.py are, and nearly every
    # tap is a cache hit that costs nothing — so it sits where a normal reading
    # session never reaches it: 60/hr cut off readers who were only tapping
    # headlines. No block_time: the library's block is per client across every
    # route, so a burst of taps would have taken the feeds and translations
    # down with it for five minutes.
    "^/v1/news/summary(/stream)?$": [
        Rule(minute=60, hour=300, zone="news-summary"),
        Rule(
            group=RateLimitGroup.pending_auth,
            minute=60,
            hour=300,
            zone="news-summary",
        ),
        Rule(group=RateLimitGroup.web, minute=120, hour=600, zone="news-summary"),
        Rule(
            group=RateLimitGroup.elevated,
            minute=120,
            hour=600,
            zone="news-summary",
        ),
    ],
    # The availability pre-check fires with every headline tap and is
    # Redis-only (one MGET), but it is still an unauthenticated route that
    # discloses per-URL state — the 500/min catch-all it used to sit in made
    # it a cheap Redis-pressure lever.
    "^/v1/news/summary/available$": [
        Rule(minute=120, hour=1200, zone="news-summary-check"),
        Rule(
            group=RateLimitGroup.pending_auth,
            minute=120,
            hour=1200,
            zone="news-summary-check",
        ),
        Rule(
            group=RateLimitGroup.web,
            minute=240,
            hour=2400,
            zone="news-summary-check",
        ),
        Rule(
            group=RateLimitGroup.elevated,
            minute=240,
            hour=2400,
            zone="news-summary-check",
        ),
    ],
    # No block_time here for the same reason as the other news zones: the
    # library's block is per client across EVERY route, so one CGNAT/office IP
    # with a handful of readers polling heatmaps tripped 60/min and took the
    # whole wall down for those readers for five minutes. The hourly window is
    # what actually bounds sustained upstream/model cost.
    "^/v1/news/(weather|translate|search|batch|heatmap)": [
        Rule(minute=60, hour=600, zone="news-proxy"),
        Rule(
            group=RateLimitGroup.pending_auth,
            minute=60,
            hour=600,
            zone="news-proxy",
        ),
        Rule(group=RateLimitGroup.web, minute=120, hour=1200, zone="news-proxy"),
        Rule(
            group=RateLimitGroup.elevated,
            minute=120,
            hour=1200,
            zone="news-proxy",
        ),
    ],
    # Followed-source routes. /followed/feed and /followed/{source_id} are
    # two-segment paths, so without this rule they fell through to the /v1
    # catch-all — yet the feed fans an MGET across the whole followed set and
    # every PUT/DELETE takes a database session. Before the generic
    # single-segment rule so it matches first.
    "^/v1/news/followed": [
        Rule(minute=240, hour=6000, zone="news-source"),
        Rule(
            group=RateLimitGroup.pending_auth,
            minute=240,
            hour=6000,
            zone="news-source",
        ),
        Rule(group=RateLimitGroup.web, minute=480, hour=12000, zone="news-source"),
        Rule(
            group=RateLimitGroup.elevated,
            minute=480,
            hour=12000,
            zone="news-source",
        ),
    ],
    # One request per source per poll, so a reader with a full deck open makes
    # more of these than of anything else — but cycling ids across the roster is
    # also the cheapest way to drive our outbound fetches, which the 500/min
    # catch-all left wide open. Sits well above a heavy reader and well below a
    # scraper. Deliberately NO block_time: the library's block applies to the
    # client across every route, so tripping this would take the whole wall down
    # for five minutes instead of slowing one endpoint. Every other
    # single-segment news route (/sources, /default-deck, /templates,
    # /crossword) shares this zone; two-segment paths other than
    # /summary/available and /followed/* (which have their own rules above)
    # fall through to the /v1 catch-all.
    "^/v1/news/[^/]+/?$": [
        Rule(minute=240, hour=6000, zone="news-source"),
        Rule(
            group=RateLimitGroup.pending_auth,
            minute=240,
            hour=6000,
            zone="news-source",
        ),
        Rule(group=RateLimitGroup.web, minute=480, hour=12000, zone="news-source"),
        Rule(
            group=RateLimitGroup.elevated,
            minute=480,
            hour=12000,
            zone="news-source",
        ),
    ],
    # Outside /v1, so the catch-all never covered it — yet every call takes a
    # database session from the pool plus a Redis round trip. Generous enough
    # for the uptime probes and the container health check (one every few
    # seconds each), tight enough that it can't be used to drain the pool.
    "^/healthz": [
        Rule(minute=120, zone="healthz"),
        Rule(group=RateLimitGroup.pending_auth, minute=120, zone="healthz"),
        Rule(group=RateLimitGroup.web, minute=120, zone="healthz"),
        Rule(group=RateLimitGroup.elevated, minute=120, zone="healthz"),
    ],
    # Anonymous OAuth2 dynamic client registration (RFC 7591).
    "^/v1/oauth2/register": [
        Rule(hour=10, block_time=3600, zone="oauth2-register"),
        Rule(
            group=RateLimitGroup.pending_auth,
            hour=10,
            block_time=3600,
            zone="oauth2-register",
        ),
    ],
}

_SANDBOX_RULES: dict[str, Sequence[Rule]] = {
    **_BASE_RULES,
    "^/v1": [
        Rule(group=RateLimitGroup.restricted, minute=10, zone="api"),
        Rule(group=RateLimitGroup.default, minute=100, zone="api"),
        Rule(group=RateLimitGroup.web, second=50, zone="api"),
        Rule(group=RateLimitGroup.elevated, second=50, zone="api"),
        Rule(group=RateLimitGroup.pending_auth, minute=60, zone="api"),
    ],
}

_PRODUCTION_RULES: dict[str, Sequence[Rule]] = {
    **_BASE_RULES,
    "^/v1": [
        Rule(group=RateLimitGroup.restricted, minute=60, zone="api"),
        Rule(group=RateLimitGroup.default, minute=500, zone="api"),
        Rule(group=RateLimitGroup.web, second=100, zone="api"),
        Rule(group=RateLimitGroup.elevated, second=100, zone="api"),
        Rule(group=RateLimitGroup.pending_auth, minute=60, zone="api"),
    ],
}


def get_middleware(app: ASGIApp, redis: Redis) -> RateLimitMiddleware:
    match settings.ENV:
        case Environment.production:
            rules = _PRODUCTION_RULES
        case Environment.sandbox:
            rules = _SANDBOX_RULES
        case _:
            rules = {}

    async def _on_auth_error(exc: Exception) -> ASGIApp:
        # Fail OPEN. The limiter protects upstreams, not data integrity, and
        # the news wall is public and anonymous — if Redis is unreachable,
        # serving unlimited traffic beats 500ing every request on the site.
        log.warning("rate_limit.unavailable", error=str(exc))
        return app

    return RateLimitMiddleware(
        app,
        partial(_authenticate, redis=redis),
        RedisBackend(redis),
        rules,
        on_auth_error=_on_auth_error,
    )


__all__ = [
    "clear_cached_identity",
    "get_middleware",
    "write_cached_identity",
]
