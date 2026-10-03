"""The midnight rotation: the day's approved products go live, yesterday's
end, and the card is rebuilt."""

import structlog

from outception.redis import create_redis
from outception.worker import (
    AsyncSessionMaker,
    CronTrigger,
    TaskPriority,
    TaskQueue,
    actor,
)

from . import service

log = structlog.get_logger()


@actor(
    actor_name="launches.rotate_day",
    cron_trigger=CronTrigger(hour=0, minute=0),
    queue_name=TaskQueue.NEWS_PIPELINE,
    priority=TaskPriority.LOW,
    max_retries=0,
    time_limit=5 * 60 * 1000,
)
async def rotate_day() -> None:
    redis = create_redis("worker")
    try:
        async with AsyncSessionMaker() as session:
            counts = await service.rotate_day(session, redis)
            await session.commit()
    finally:
        await redis.close()
    log.info("launches.rotate_day", **counts)
