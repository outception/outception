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

import structlog

from outception.config import settings
from outception.redis import create_redis
from outception.worker import CronTrigger, TaskPriority, actor

from . import cache, translate
from .endpoints import DEFAULT_DECK, DISABLED_SOURCES, WEATHER_DECK_ID
from .metadata import SOURCES

log = structlog.get_logger()


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
    try:
        for source_id in _deck_sources():
            entry = await cache.get(redis, source_id)
            if entry is None:
                continue
            titles = [item.title for item in entry.items if item.title]
            if not titles:
                continue
            for language in languages:
                await translate.translate_texts(redis, titles, language)
                warmed += 1
    finally:
        await redis.close()

    log.info("news.warm_translations", languages=len(languages), warmed=warmed)
