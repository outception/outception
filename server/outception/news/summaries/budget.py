"""The summary path's memory and brakes: the result caches, the failure
markers (short for a transient failure, a day for a definitive one), the
per-publisher brake, the daily summary budget with its warm and
speculative sub-budgets, and the per-URL fan-out cap. The model lanes
and the paid cap are the governor's; these are the product's own rules on
top of them, and every key name is as the live tree wrote it."""

import hashlib
from datetime import UTC, datetime
from urllib.parse import urlsplit

import structlog

from outception.redis import Redis

from .. import gnews
from ..fetch import NewsFetchError, UnsafeURLError
from .errors import LiveDeadlinePassed

log = structlog.get_logger()

CACHE_KEY = "news:summary:{digest}"
CACHE_TTL_SECONDS = 7 * 24 * 60 * 60
# The publisher's own standfirst, cached per (url, lang) for a day.
TEASER_CACHE_KEY = "news:summary:teaser:{digest}"
TEASER_CACHE_TTL_SECONDS = 24 * 60 * 60
# A failing article (paywall, bot wall, too little text) must not be
# retried on every tap: fail fast from the marker for a couple of minutes.
FAIL_KEY = "news:summary:fail:{digest}"
FAIL_TTL_SECONDS = 120
# Definitive failures (the page is not an article, the aggregator link
# cannot be resolved, the publisher blocks even the reader) do not heal in
# minutes: remember them for a day so the tap goes straight to the article.
# "too short" is deliberately not here: a slow page that served only a
# stub this once heals on the next fetch.
DEAD_TTL_SECONDS = 24 * 60 * 60
DEFINITIVE_FAILURES = (
    "not the article",
    "could not be resolved",
    "unsafe",
    "reader fallback failed: Client error",
)
# A publisher that keeps shutting the fetcher out is treated as unavailable
# as a whole for a while. Only failures that speak for the publisher count;
# a page that is simply not an article says nothing about its neighbours.
HOST_FAILURES = (
    "HTTP 401",
    "HTTP 403",
    "not the article",
    "reader fallback failed: Client error",
)
HOST_FAIL_KEY = "news:summary:hostfail:{host}"
# One failing article may be re-tapped forever without speaking for its
# host: only distinct URLs count towards the limit.
HOST_FAIL_SEEN_KEY = "news:summary:hostfail:seen:{host}:{url_hash}"
HOST_FAIL_TTL_SECONDS = 6 * 60 * 60
HOST_FAIL_LIMIT = 3
DAILY_KEY = "news:summary:daily:{day}"
WARM_DAILY_KEY = "news:summary:warmday:{day}"
# Speculative warming is counted separately from warming for cards readers
# actually opened, so it can have a budget of its own.
PRETAP_DAILY_KEY = "news:summary:pretapday:{day}"
# One article legitimately gets summarized a handful of times a day; every
# known URL times every variant is a distinct digest and a fresh model
# call, which made the whole daily budget anonymously drainable. Counted
# only when a generation is really about to run.
URL_FANOUT_KEY = "news:summary:urlday:{digest}:{day}"
URL_FANOUT_DAILY_CAP = 8
# A deadline miss is remembered like any other fresh failure, but with a
# value the warmer knows to ignore, or the handoff would be skipped as a
# known failure.
FAIL_HANDOFF = "handoff"


def today() -> str:
    return datetime.now(UTC).strftime("%Y%m%d")


def digest(url: str, lang: str) -> str:
    return hashlib.sha256(f"{url}|{lang}".encode()).hexdigest()[:32]


def host(url: str) -> str:
    try:
        return urlsplit(url).hostname or ""
    except ValueError:
        return ""


def is_definitive(exc: BaseException) -> bool:
    if isinstance(exc, UnsafeURLError):
        return True
    reason = str(exc)
    if not isinstance(exc, NewsFetchError) or "429" in reason:
        return False
    return any(marker in reason for marker in DEFINITIVE_FAILURES)


def is_host_failure(exc: BaseException) -> bool:
    reason = str(exc)
    if not isinstance(exc, NewsFetchError) or "429" in reason:
        return False
    return any(marker in reason for marker in HOST_FAILURES)


async def daily_used(redis: Redis) -> int:
    return int(await redis.get(DAILY_KEY.format(day=today())) or 0)


async def url_fanout_exceeded(redis: Redis, url: str) -> bool:
    key = URL_FANOUT_KEY.format(digest=digest(url, "urlday"), day=today())
    count = int(await redis.incr(key))
    if count == 1:
        await redis.expire(key, 2 * 24 * 60 * 60)
    if count > URL_FANOUT_DAILY_CAP:
        log.warning("news.summary_url_fanout_cap", url=url, count=count)
        return True
    return False


async def charge_daily(
    redis: Redis, *, warm: bool = False, pretap: bool = False
) -> None:
    """Spend one unit of the day's summary budget, with the article text
    already in hand and a model call about to go out. Charging any earlier
    let pages that never reach a model burn the budget every reader shares.
    `warm` charges the warmer's own sub-budget in the same breath, so the
    reader-spend brake (total minus warm) never lies; `pretap` additionally
    charges the speculative sub-budget."""
    day = today()
    if await redis.incr(DAILY_KEY.format(day=day)) == 1:
        await redis.expire(DAILY_KEY.format(day=day), 2 * 24 * 60 * 60)
    if warm and await redis.incr(WARM_DAILY_KEY.format(day=day)) == 1:
        await redis.expire(WARM_DAILY_KEY.format(day=day), 2 * 24 * 60 * 60)
    if pretap and await redis.incr(PRETAP_DAILY_KEY.format(day=day)) == 1:
        await redis.expire(PRETAP_DAILY_KEY.format(day=day), 2 * 24 * 60 * 60)


async def host_blocked(redis: Redis, url: str) -> bool:
    name = host(url)
    if not name or gnews.is_google_news_url(url):
        return False
    failures = await redis.get(HOST_FAIL_KEY.format(host=name))
    return int(failures or 0) >= HOST_FAIL_LIMIT


async def mark_failed(redis: Redis, url: str, key: str, exc: BaseException) -> None:
    if isinstance(exc, LiveDeadlinePassed):
        await redis.set(FAIL_KEY.format(digest=key), FAIL_HANDOFF, ex=FAIL_TTL_SECONDS)
        return
    if not is_definitive(exc):
        await redis.set(FAIL_KEY.format(digest=key), "1", ex=FAIL_TTL_SECONDS)
        return
    await redis.set(FAIL_KEY.format(digest=key), "1", ex=DEAD_TTL_SECONDS)
    name = host(url)
    if name and is_host_failure(exc) and not gnews.is_google_news_url(url):
        # Count each article once: re-tapping one failing URL must not reach
        # the limit.
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:32]
        seen_key = HOST_FAIL_SEEN_KEY.format(host=name, url_hash=url_hash)
        if not await redis.set(seen_key, "1", ex=HOST_FAIL_TTL_SECONDS, nx=True):
            return
        host_key = HOST_FAIL_KEY.format(host=name)
        failures = await redis.incr(host_key)
        if failures == 1:
            await redis.expire(host_key, HOST_FAIL_TTL_SECONDS)
        if failures == HOST_FAIL_LIMIT:
            log.info("news.summary_host_blocked", host=name)


async def mark_succeeded(redis: Redis, url: str, key: str, summary: str) -> None:
    await redis.set(CACHE_KEY.format(digest=key), summary, ex=CACHE_TTL_SECONDS)
    name = host(url)
    if name:
        await redis.delete(HOST_FAIL_KEY.format(host=name))
