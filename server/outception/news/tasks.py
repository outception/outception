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
import time

import structlog

from outception.config import settings
from outception.locker import Locker, TimeoutLockError
from outception.redis import create_redis
from outception.worker import CronTrigger, TaskPriority, actor

from . import cache, translate
from .endpoints import DEFAULT_DECK, WEATHER_DECK_ID
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
