"""Background translation warming for the default deck.

The wall renders headlines in the reader's language via on-demand machine
translation (``GET /news/{id}?lang=xx``). The very first reader in a given
language pays for the cold translation of a whole card; this warmer pays it for
them ahead of time, on a schedule, so the default spread is already translated
into every UI language in the Redis cache.

It never fetches news — that's deliberate (the old source cache-warmer was
removed for hammering upstreams). It only translates headlines that are
*already cached*; a source with no warm cache is simply skipped this round and
picked up once a reader (or the source's own on-demand fetch) has populated it.
"""

import asyncio
import bisect
import json
import random
import time

import structlog

# The API process registers source getters via its own import in api.py; the
# WORKER runs this module without ever touching api.py, so without this import
# registry.GETTERS is empty here and the warmer silently warms nothing
# (stale=2358, fetched=0 in prod logs).
import outception.news.sources  # noqa: F401 — registers source getters
from outception.config import settings
from outception.locker import Locker, TimeoutLockError
from outception.redis import Redis, create_redis
from outception.worker import CronTrigger, TaskPriority, actor

from . import cache, heatmap, registry, translate
from .endpoints import DEFAULT_DECK, SOURCE_DEMAND_KEY, WEATHER_DECK_ID
from .metadata import SOURCES
from .registry import DISABLED_SOURCES

log = structlog.get_logger()

# The cron fires every 30 min. Stop well before the next tick so two runs can
# never overlap and double our outbound pressure on the translation endpoint.
_RUN_BUDGET_SECONDS = 20 * 60
_LOCK_NAME = "news.warm_translations"


def _warm_languages() -> list[str]:
    return [
        lang.strip()
        for lang in settings.TRANSLATION_WARM_LANGUAGES.split(",")
        if lang.strip()
    ]


def _deck_sources() -> list[str]:
    return [
        sid
        for sid in DEFAULT_DECK
        if sid != WEATHER_DECK_ID and sid in SOURCES and sid not in DISABLED_SOURCES
    ]


@actor(
    actor_name="news.warm_translations",
    cron_trigger=CronTrigger(minute="*/30"),
    priority=TaskPriority.LOW,
    max_retries=0,
)
async def warm_translations() -> None:
    """Pre-translate the default deck's cached headlines into every warm
    language, cache-first. Does not fetch: uncached sources are skipped."""
    languages = _warm_languages()
    if not languages:
        return

    redis = create_redis("worker")
    warmed = 0
    deadline = time.monotonic() + _RUN_BUDGET_SECONDS
    timed_out = False
    try:
        # A run is sources x languages translations; cold, that can outlast the
        # 30-min cron interval. Without the lock the next tick starts anyway and
        # both runs hammer the keyless upstream, which gets our egress IP banned.
        async with Locker(redis).lock(
            _LOCK_NAME, timeout=_RUN_BUDGET_SECONDS + 60, blocking_timeout=0
        ):
            for source_id in _deck_sources():
                entry = await cache.get(redis, source_id)
                if entry is None:
                    continue
                titles = [item.title for item in entry.items if item.title]
                if not titles:
                    continue
                if time.monotonic() > deadline:
                    timed_out = True
                    break
                # Fan out across languages — translate_texts has its own
                # concurrency cap, so this stays bounded while turning a
                # 46-step sequential wait into one.
                results = await asyncio.gather(
                    *(
                        translate.translate_texts(redis, titles, language)
                        for language in languages
                    ),
                    return_exceptions=True,
                )
                warmed += sum(1 for r in results if not isinstance(r, BaseException))
    except TimeoutLockError:
        log.info("news.warm_translations.already_running")
        return
    finally:
        await redis.close()

    log.info(
        "news.warm_translations",
        languages=len(languages),
        warmed=warmed,
        timed_out=timed_out,
    )


# ---- Demand-driven source warmer --------------------------------------------
#
# Wall-cache entries (news:source:{id}, 180-min TTL) normally only fill when a
# reader opens that feed. Two things break when a feed goes cold: buzz
# heatmaps render empty ("failed to load"), and a reader opening a rarely-
# viewed source pays the full upstream latency (multi-second for the slower
# scrapers) on first paint. This warmer keeps recently-viewed feeds warm
# WITHOUT recreating the old cache-warmer that was removed for hammering
# upstreams (many feeds are news.google.com RSS hit from a single egress IP):
#
#  - Demand-gated: only families of buzz maps viewed in the last 48h (see
#    heatmap._DEMAND_KEY) plus individually-viewed sources (see
#    endpoints.SOURCE_DEMAND_KEY) are warmed — never the whole roster.
#  - Serial with 2-4s jitter between fetches — no bursts, ≤ ~20 req/min.
#  - Hard per-run fetch cap + run budget, single-flight lock across workers.
#  - Circuit breaker: consecutive failures (429s, consent redirects) abort the
#    run and back the warmer off for 30 min — when the upstream pushes back,
#    we stop pushing.
#  - Rotating cursor so a capped run resumes where the last one stopped
#    instead of re-warming the same head of the list.

_BUZZ_LOCK_NAME = "news.warm_buzz_sources"
_BUZZ_RUN_BUDGET_SECONDS = 8 * 60
_BUZZ_FETCH_CAP = 120
# Refresh before the 180-min cache TTL expires, with slack for cron (10 min)
# and rotation lag.
_BUZZ_STALE_AFTER_MS = 100 * 60 * 1000
_BUZZ_JITTER_SECONDS = (2.0, 4.0)
# Hard per-fetch bound: some scrapers can hang far past their nominal
# timeouts, and a single hung getter blows through the run budget until
# dramatiq's TimeLimitExceeded kills the whole run mid-rotation (seen in prod
# 2026-08-14). A hung feed counts as a failure and the rotation moves on.
_BUZZ_FETCH_TIMEOUT_SECONDS = 20.0
_BUZZ_FAILURE_TRIP = 5
_BUZZ_BACKOFF_KEY = "news:buzz_warm:backoff"
_BUZZ_BACKOFF_SECONDS = 30 * 60
_BUZZ_CURSOR_KEY = "news:buzz_warm:cursor"
_BUZZ_CURSOR_TTL_SECONDS = 24 * 60 * 60


def _entry_is_stale(raw: str | bytes | None, now: int) -> bool:
    if raw is None:
        return True
    try:
        updated = int(json.loads(raw)["updated"])
    except (ValueError, KeyError, TypeError):
        return True
    return now - updated > _BUZZ_STALE_AFTER_MS


async def _demanded_single_sources(redis: Redis) -> set[str]:
    pattern = SOURCE_DEMAND_KEY.format(id="*")
    prefix_len = len(pattern) - 1
    demanded: set[str] = set()
    async for key in redis.scan_iter(match=pattern, count=500):
        text = key.decode() if isinstance(key, bytes) else str(key)
        demanded.add(text[prefix_len:])
    return demanded


async def _stale_demanded_sources(redis: Redis) -> list[str]:
    family_ids = await _demanded_single_sources(redis)
    for heatmap_id in await heatmap.demanded_buzz_ids(redis):
        family_ids.update(
            source_id
            for source_id, _, _ in heatmap.buzz_family(heatmap.HEATMAPS[heatmap_id])
        )
    family_ids.difference_update(DISABLED_SOURCES)

    now = cache.now_ms()
    ids = sorted(family_ids)
    stale: list[str] = []
    for start in range(0, len(ids), 250):
        for source_id, raw in await cache.mget_hot_raw(redis, ids[start : start + 250]):
            if _entry_is_stale(raw, now):
                stale.append(source_id)
    return stale


@actor(
    actor_name="news.warm_demanded_sources",
    cron_trigger=CronTrigger(minute="*/10"),
    priority=TaskPriority.LOW,
    max_retries=0,
    # Comfortably above the 8-min run budget + one 20s fetch of slack; the
    # dramatiq default (10 min) was killing runs mid-rotation.
    time_limit=12 * 60 * 1000,
)
async def warm_demanded_sources() -> None:
    """Gently refetch recently-viewed wall feeds — the families behind viewed
    buzz heatmaps plus individually-viewed sources — so maps always have
    stories to build tiles from and returning readers never pay a cold
    upstream fetch on first paint."""
    redis = create_redis("worker")
    fetched = 0
    stale_count = 0
    tripped = False
    try:
        async with Locker(redis).lock(
            _BUZZ_LOCK_NAME,
            timeout=_BUZZ_RUN_BUDGET_SECONDS + 60,
            blocking_timeout=0,
        ):
            if await redis.get(_BUZZ_BACKOFF_KEY):
                return
            stale = await _stale_demanded_sources(redis)
            stale_count = len(stale)
            if not stale:
                return

            # Resume after the last warmed id so capped runs cover the whole
            # rotation instead of re-warming the same alphabetical head.
            cursor_raw = await redis.get(_BUZZ_CURSOR_KEY)
            if cursor_raw:
                cursor = (
                    cursor_raw.decode()
                    if isinstance(cursor_raw, bytes)
                    else str(cursor_raw)
                )
                pivot = bisect.bisect_right(stale, cursor)
                stale = stale[pivot:] + stale[:pivot]

            deadline = time.monotonic() + _BUZZ_RUN_BUDGET_SECONDS
            attempts = 0
            failures = 0
            for source_id in stale:
                if attempts >= _BUZZ_FETCH_CAP or time.monotonic() > deadline:
                    break
                getter = registry.GETTERS.get(source_id)
                if getter is None:
                    continue
                attempts += 1
                try:
                    items = (
                        await asyncio.wait_for(
                            getter(), timeout=_BUZZ_FETCH_TIMEOUT_SECONDS
                        )
                    )[:30]
                    await cache.set(redis, source_id, items)
                    fetched += 1
                    failures = 0
                except Exception as exc:  # scrapers parse wild HTML
                    failures += 1
                    log.info(
                        "news.buzz_warm_fetch_failed",
                        source=source_id,
                        error=str(exc),
                    )
                    if failures >= _BUZZ_FAILURE_TRIP:
                        tripped = True
                        await redis.set(
                            _BUZZ_BACKOFF_KEY, "1", ex=_BUZZ_BACKOFF_SECONDS
                        )
                        break
                await redis.set(
                    _BUZZ_CURSOR_KEY, source_id, ex=_BUZZ_CURSOR_TTL_SECONDS
                )
                await asyncio.sleep(random.uniform(*_BUZZ_JITTER_SECONDS))
    except TimeoutLockError:
        log.info("news.warm_buzz_sources.already_running")
        return
    finally:
        await redis.close()

    if tripped:
        log.warning(
            "news.buzz_warm_tripped",
            fetched=fetched,
            backoff_seconds=_BUZZ_BACKOFF_SECONDS,
        )
    else:
        log.info("news.buzz_warm_done", stale=stale_count, fetched=fetched)
