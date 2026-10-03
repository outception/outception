"""The scorer and the builder, gated by BRIEFING_ENABLED until production
data exists; clustering runs regardless so the publisher count exists at
swap time."""

import structlog
from redis import RedisError

from outception.config import settings
from outception.redis import create_redis
from outception.worker import (
    AsyncSessionMaker,
    CronTrigger,
    TaskPriority,
    TaskQueue,
    actor,
)

from ..clusters import repository
from ..clusters import service as clusters
from . import builder, scorer
from .profiles import enabled_profile_ids, profiles
from .router import by_sources

log = structlog.get_logger()


async def route_recent(session: object, redis: object, hours: int = 2) -> int:
    """Put every cluster seen in the window on the pending set of each
    profile its publishers belong to. Idempotent: the scorer skips what
    it scored within a day."""
    enabled = {pid: profiles()[pid] for pid in enabled_profile_ids()}
    routed = 0
    for cluster in await repository.recent(session, hours=hours):  # type: ignore[arg-type]
        members = await repository.members(session, cluster.id)  # type: ignore[arg-type]
        source_ids = {member.source_id for member in members}
        for pid in by_sources(source_ids, enabled):
            await scorer.note_pending(redis, pid, [cluster.id])  # type: ignore[arg-type]
            routed += 1
    return routed


@actor(
    actor_name="news.score_clusters",
    cron_trigger=CronTrigger(minute="*/15"),
    queue_name=TaskQueue.NEWS_PIPELINE,
    priority=TaskPriority.LOW,
    max_retries=0,
    time_limit=12 * 60 * 1000,
)
async def score_clusters() -> None:
    if not settings.BRIEFING_ENABLED or settings.LLM_DISABLED:
        return
    redis = create_redis("worker")
    try:
        async with AsyncSessionMaker() as session:
            routed = await route_recent(session, redis)
            await session.commit()
            for pid in enabled_profile_ids():
                stats = await scorer.score_pending(session, redis, profiles()[pid])
                log.info(
                    "news.score_clusters",
                    profile=pid,
                    scored=stats.scored,
                    nulls=stats.nulls,
                    deferred=stats.deferred,
                    routed=routed,
                )
                if stats.deferred:
                    break
    except RedisError as exc:
        log.info("news.score_clusters.redis_unavailable", error=str(exc))
    finally:
        await redis.close()


@actor(
    actor_name="news.build_briefing",
    cron_trigger=CronTrigger(minute=5),
    queue_name=TaskQueue.NEWS_PIPELINE,
    priority=TaskPriority.LOW,
    max_retries=0,
    time_limit=10 * 60 * 1000,
)
async def build_briefing() -> None:
    if not settings.BRIEFING_ENABLED:
        return
    redis = create_redis("worker")
    try:
        async with AsyncSessionMaker() as session:
            for pid in enabled_profile_ids():
                await builder.build(session, redis, profiles()[pid])
                await session.commit()
    except RedisError as exc:
        log.info("news.build_briefing.redis_unavailable", error=str(exc))
    finally:
        await redis.close()


__all__ = ["build_briefing", "clusters", "score_clusters"]
