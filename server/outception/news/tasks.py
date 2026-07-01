"""Background cache-warmer for the public news wall.

The wall is cache-first: ``POST /news/batch`` only ever returns warm Redis
entries and each card lazily fetches its own source on a cache miss. Without
warming, a cold cache makes every visitor's cards fetch upstream live
(throttled 8-at-a-time by the shared fetch semaphore), so the wall trickles
in slowly — most visibly for the ~179 Reddit channels, which Reddit also
rate-limits by IP.

This periodic actor pre-fetches every registered source into Redis so the
wall serves instantly from cache. It reuses the endpoint's ``_get_source``
path (same fetch semaphore, TTL semantics, and stale-on-failure fallback);
sources still fresh within their interval return from cache without a
refetch, so a run only refreshes what has actually aged out.
"""

import asyncio

import structlog

from outception.worker import CronTrigger, RedisMiddleware, TaskPriority, actor

from . import registry
from .endpoints import DISABLED_SOURCES, _get_source

log = structlog.get_logger()


@actor(
    actor_name="news.warm_cache",
    cron_trigger=CronTrigger(minute="*/5"),
    priority=TaskPriority.LOW,
    max_retries=0,
)
async def news_warm_cache() -> None:
    redis = RedisMiddleware.get()
    source_ids = [sid for sid in registry.GETTERS if sid not in DISABLED_SOURCES]

    async def warm(source_id: str) -> bool:
        try:
            await _get_source(redis, source_id, latest=True)
            return True
        except Exception as exc:  # a single dead source must not fail the batch
            log.info("news.warm_failed", source=source_id, error=str(exc))
            return False

    results = await asyncio.gather(*(warm(sid) for sid in source_ids))
    log.info("news.warm_cache_done", total=len(source_ids), warmed=sum(results))
