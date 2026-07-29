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

from . import cache, heatmap, registry, summary, translate
from .endpoints import (
    DEFAULT_DECK,
    SOURCE_DEMAND_KEY,
    SOURCE_DEMAND_TTL_SECONDS,
    WEATHER_DECK_ID,
    _ordered_sources,
)
from .fetch import FETCH_TIMEOUT_SECONDS, StaleFeedError
from .metadata import SOURCES
from .registry import DISABLED_SOURCES

log = structlog.get_logger()

# The cron fires every 10 min. Stop well before the next tick so two runs can
# never overlap and double our outbound pressure on the translation endpoint.
_RUN_BUDGET_SECONDS = 8 * 60
# Source translations one warm run may start that actually need the model
# (cache hits are free and don't count): a single run can no longer sweep the
# whole deck into every demanded language at once.
_WARM_RUN_BATCH_CAP = 200
# Sources translated concurrently within one language — low, so background
# warming never crowds live readers on the same provider.
_WARM_CONCURRENCY = 3
# Paid batches one run may spend: spreads the warmer's daily paid allowance
# over the day instead of burning it all in the first cold run.
_WARM_RUN_PAID_CAP = 30
# Warm only the languages readers actually use. Demand is ranked, and its tail
# is long and thin: warming all of it spent the free tier (and then the paid
# allowance) on languages nobody was waiting for, so the warmer failed for
# everyone. The tail still translates on demand — one reader waits ~2s once,
# and it is cached for the rest.
_WARM_LANGUAGE_CAP = 8
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
    cron_trigger=CronTrigger(minute="*/10"),
    priority=TaskPriority.LOW,
    max_retries=0,
    # Above the run budget plus one in-flight source; the broker's 60s default
    # TimeLimit was killing every run a minute in.
    time_limit=(_RUN_BUDGET_SECONDS + 120) * 1000,
)
async def warm_translations() -> None:
    """Pre-translate the default deck's cached headlines into the languages
    readers asked for recently — the most-read language first, so the cards
    people actually open are warm before they swipe to them. Cache-first and
    incremental: once a language is warm, a run only translates the headlines
    that appeared since. Does not fetch: uncached sources are skipped."""
    allowed = set(_warm_languages())
    if not allowed:
        return

    redis = create_redis("worker")
    if await translate.warmer_out_of_budget(redis):
        # Out of both free share and paid allowance until the daily reset:
        # every attempt would only seize chunk claims from live readers and
        # fail (see translate.warmer_out_of_budget).
        log.info("news.warm_translations.out_of_budget")
        await redis.close()
        return
    warmed = 0
    languages: list[str] = []
    deadline = time.monotonic() + _RUN_BUDGET_SECONDS
    timed_out = False
    try:
        # Without the lock the next tick starts anyway and both runs double the
        # model spend for nothing.
        async with Locker(redis).lock(
            _LOCK_NAME, timeout=_RUN_BUDGET_SECONDS + 60, blocking_timeout=0
        ):
            languages = [
                lang
                for lang in await translate.demanded_targets(redis)
                if lang in allowed
            ][:_WARM_LANGUAGE_CAP]
            started = 0
            paid_at_start = await translate.paid_used(redis, "warmer")
            gate = asyncio.Semaphore(_WARM_CONCURRENCY)

            async def paid_exhausted() -> bool:
                # Both the per-run brake and the daily one: budgets can run
                # out mid-run, and past that point every further batch is a
                # claim seized from live readers and then failed.
                spent = await translate.paid_used(redis, "warmer") - paid_at_start
                if spent >= _WARM_RUN_PAID_CAP:
                    return True
                return await translate.warmer_out_of_budget(redis)

            async def warm_one(titles: list[str], language: str) -> bool:
                async with gate:
                    await translate.translate_texts(
                        redis, titles, language, budget="warmer"
                    )
                    return True

            # One cache read + parse per source for the whole run. Reading
            # inside the language loop re-fetched and re-validated every
            # entry once per language — ~8,000 model_validate calls per run
            # for ~33 distinct payloads.
            source_titles: dict[str, list[str]] = {}
            for source_id in _deck_sources():
                entry = await cache.get(redis, source_id)
                if entry is None:
                    continue
                titles = [item.title for item in entry.items if item.title]
                if titles:
                    source_titles[source_id] = titles

            for language in languages:
                if started >= _WARM_RUN_BATCH_CAP or time.monotonic() > deadline:
                    break
                # Checked once per language, then again only after the
                # language's batches land: the paid counter only moves when
                # this task spends it, so polling it per source was 200+
                # reads per run for a value that changes between languages.
                if await paid_exhausted():
                    break
                pending: list[asyncio.Task[bool]] = []
                for titles in source_titles.values():
                    if started >= _WARM_RUN_BATCH_CAP:
                        break
                    if time.monotonic() > deadline:
                        timed_out = True
                        break
                    if not await translate.uncached_count(redis, titles, language):
                        continue
                    started += 1
                    pending.append(asyncio.create_task(warm_one(titles, language)))
                results = await asyncio.gather(*pending, return_exceptions=True)
                warmed += sum(1 for r in results if r is True)
                if timed_out:
                    break
    except TimeoutLockError:
        log.info("news.warm_translations.already_running")
        return
    finally:
        await redis.close()

    log.info(
        "news.warm_translations",
        languages=len(languages),
        top=languages[:5],
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
# 2026-08-14). A hung feed counts as a failure and the rotation moves on. The
# request path applies the same bound (see fetch.FETCH_TIMEOUT_SECONDS).
_BUZZ_FETCH_TIMEOUT_SECONDS = FETCH_TIMEOUT_SECONDS
_BUZZ_FAILURE_TRIP = 5
_BUZZ_BACKOFF_KEY = "news:buzz_warm:backoff"
_BUZZ_BACKOFF_SECONDS = 30 * 60
_BUZZ_CURSOR_KEY = "news:buzz_warm:cursor"
_BUZZ_CURSOR_TTL_SECONDS = 24 * 60 * 60
# Headlines per freshly-warmed card queued for summary pre-warming ("pre-tap").
# Three rather than the serve path's six: the roster-wide sweep multiplies by
# ~330 sources, and 330×3 a day already sits at the warm budget's edge — the
# serve path deepens coverage to six for the cards people actually open.
_PRETAP_HERO_COUNT = 3

# Sources kept warm whether or not anyone has opened them.
#
# Headline search can only see what is cached, and the cache only holds what
# readers have viewed — so with light traffic a search covered barely a hundred
# sources out of ten thousand, and the big outlets people actually search for
# were usually missing. These ride the SAME rotation as demanded sources, so
# they inherit its whole safety envelope: one fetch at a time, 2-4s of jitter
# between them, a per-run cap, a per-fetch timeout, and the consecutive-failure
# breaker. That envelope is the point — an earlier warmer that swept the roster
# without it hammered publishers and had to be removed.
#
# Sized against the rotation rather than picked for roundness: refreshing a
# source every _BUZZ_STALE_AFTER_MS costs one fetch, the cron gives ten runs of
# up to _BUZZ_FETCH_CAP in that window, so the ceiling is ~1,200 sources. Well
# under it, leaving most of the rotation free for whatever readers are actually
# viewing — they must never be crowded out by this.
_ALWAYS_WARM_COUNT = 300

# The deck a new reader lands on, then the head of the roster — which
# `_ordered_sources` sorts by column priority, so this is the majors (npr,
# nytimes, bbc, guardian…) rather than an arbitrary slice. Built at import
# time, which is safe here: `import outception.news.sources` above has already
# registered the getters.
ALWAYS_WARM_IDS: frozenset[str] = frozenset(
    [
        source_id
        for source_id in DEFAULT_DECK
        if source_id in registry.GETTERS and source_id not in DISABLED_SOURCES
    ]
    + [
        source_id
        for source_id, _ in _ordered_sources()
        if source_id in registry.GETTERS and source_id not in DISABLED_SOURCES
    ][:_ALWAYS_WARM_COUNT]
)


def _entry_is_stale(raw: str | bytes | None, now: int) -> bool:
    if raw is None:
        return True
    try:
        updated = int(json.loads(raw)["updated"])
    except (ValueError, KeyError, TypeError):
        return True
    return now - updated > _BUZZ_STALE_AFTER_MS


async def _demanded_single_sources(redis: Redis) -> set[str]:
    """Sources viewed in the demand window, from the single demand zset.
    Two O(log n) ops — the per-key form this replaces SCANned the entire
    keyspace (translation and known-headline keys included, hundreds of
    thousands of keys) every run to recover a few dozen ids."""
    horizon = time.time() - SOURCE_DEMAND_TTL_SECONDS
    await redis.zremrangebyscore(SOURCE_DEMAND_KEY, "-inf", horizon)
    members = await redis.zrange(SOURCE_DEMAND_KEY, 0, -1)
    return {
        member.decode() if isinstance(member, bytes) else str(member)
        for member in members
    }


async def _stale_demanded_sources(redis: Redis) -> list[str]:
    family_ids = await _demanded_single_sources(redis)
    # The always-warm set joins the same rotation as genuine demand rather than
    # getting a pass of its own — one queue means one set of caps.
    family_ids.update(ALWAYS_WARM_IDS)
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
                    if not items:
                        # Same guard as the request path (see _get_source):
                        # carry the last good set through a momentary empty,
                        # bounded by the empty-since marker rather than the
                        # entry age — cache.set re-stamps `updated`, so age
                        # alone can never exceed the TTL.
                        entry = await cache.get(redis, source_id)
                        if entry is not None and entry.items:
                            empty_key = f"news:empty-since:{source_id}"
                            empty_since = await redis.get(empty_key)
                            if empty_since is None:
                                await redis.set(
                                    empty_key,
                                    str(cache.now_ms()),
                                    ex=2 * cache.TTL_MS // 1000,
                                )
                                items = entry.items
                            elif cache.now_ms() - int(empty_since) < cache.TTL_MS:
                                items = entry.items
                    else:
                        await redis.delete(f"news:empty-since:{source_id}")
                    await cache.set(redis, source_id, items)
                    # Pre-tap the fresh card: queue its top headlines for
                    # summarization the moment the warmer discovers them,
                    # instead of waiting for the first human tap to do it —
                    # which for the always-warm majors (searchable but rarely
                    # opened) could be days after the story broke. English
                    # only: per-language warming stays demand-driven (card
                    # serves queue the viewer's language). The existing rails
                    # bound the spend — the warm set dedupes and caps at 500,
                    # already-summarized entries skip for free, and the daily
                    # warm budget brakes whatever remains.
                    for item in items[:_PRETAP_HERO_COUNT]:
                        if item.url:
                            await summary.note_warm_candidate(redis, item.url, "en")
                    fetched += 1
                    failures = 0
                except StaleFeedError as exc:
                    # Abandoned upstream: cache the emptiness rather than keep
                    # the fossils warm (same call as the request path makes).
                    log.info("news.feed_abandoned", source=source_id, error=str(exc))
                    await cache.set(redis, source_id, [])
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


# ---- Hero-summary warmer ----------------------------------------------------
#
# Serving a card queues its hero headline (summary.note_warm_candidate); this
# drains that queue so the first tap on a hero is a cache hit. Free tier only:
# warm_summary never calls the paid backup and stands down once live taps have
# used half the global budget. Serial with jitter (article fetches hit the
# same upstreams as the scrapers); a run of consecutive failures usually means
# the free quota is exhausted for the day — stop instead of burning the queue.

_SUMMARY_WARM_LOCK = "news.warm_summaries"
_SUMMARY_WARM_RUN_BUDGET_SECONDS = 8 * 60
# Raised with the per-card candidate count (endpoints._WARM_HERO_COUNT): the
# daily cap is the real governor, and a 30-per-run drain left the queue
# growing faster than it emptied, so taps kept missing the cache. At ~7s per
# candidate this still finishes inside the run budget.
_SUMMARY_WARM_RUN_CAP = 60
# The cap counts model calls, so skips (already cached, budget spent, this
# minute's free slot taken) are free and must not consume it — already-warm
# heroes were burning the whole run's allowance without summarizing anything.
# A queue that is nothing but skips would then spin, so draws are bounded too.
_SUMMARY_WARM_DRAW_CAP = _SUMMARY_WARM_RUN_CAP * 6
_SUMMARY_WARM_FAILURE_FUSE = 4
_SUMMARY_WARM_JITTER_SECONDS = (1.0, 3.0)


@actor(
    actor_name="news.warm_summaries",
    # */5, not */10: a just-published headline can't be pre-summarized before
    # it exists, so the cron interval IS the freshness lag — ten minutes of
    # readers paying the cold ~2s on every brand-new story. Runs that overrun
    # the shorter interval are safe: the lock below is non-blocking, so an
    # overlapping tick logs already_running and skips.
    cron_trigger=CronTrigger(minute="*/5"),
    priority=TaskPriority.LOW,
    max_retries=0,
    time_limit=(_SUMMARY_WARM_RUN_BUDGET_SECONDS + 120) * 1000,
)
async def warm_summaries() -> None:
    """Pre-summarize queued hero headlines so first taps land on cache."""
    redis = create_redis("worker")
    warmed = failed = skipped = 0
    consecutive_failures = 0
    deadline = time.monotonic() + _SUMMARY_WARM_RUN_BUDGET_SECONDS
    try:
        async with Locker(redis).lock(
            _SUMMARY_WARM_LOCK,
            timeout=_SUMMARY_WARM_RUN_BUDGET_SECONDS + 60,
            blocking_timeout=0,
        ):
            draws = 0
            while (
                warmed + failed < _SUMMARY_WARM_RUN_CAP
                and draws < _SUMMARY_WARM_DRAW_CAP
                and time.monotonic() < deadline
            ):
                candidate = await summary.pop_warm_candidate(redis)
                if candidate is None:
                    break
                draws += 1
                url, lang = candidate
                outcome = await summary.warm_summary(redis, url, lang)
                if outcome == "warmed":
                    warmed += 1
                    consecutive_failures = 0
                elif outcome == "failed":
                    failed += 1
                    consecutive_failures += 1
                    if consecutive_failures >= _SUMMARY_WARM_FAILURE_FUSE:
                        break
                else:
                    skipped += 1
                if outcome != "skipped":
                    await asyncio.sleep(random.uniform(*_SUMMARY_WARM_JITTER_SECONDS))
    except TimeoutLockError:
        log.info("news.warm_summaries.already_running")
        return
    finally:
        await redis.close()

    log.info("news.warm_summaries", warmed=warmed, failed=failed, skipped=skipped)
