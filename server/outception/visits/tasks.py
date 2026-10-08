"""The hourly sync: the counter's daily totals into site_visits."""

import structlog
from sqlalchemy.exc import SQLAlchemyError

from outception.integrations.counter import service as counter
from outception.integrations.counter.exceptions import CounterError
from outception.locker import Locker, TimeoutLockError
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

SYNC_LOCK = "visits.sync"
SYNC_SECONDS = 5 * 60


@actor(
    actor_name="visits.sync",
    cron_trigger=CronTrigger(minute=7),
    queue_name=TaskQueue.NEWS_PIPELINE,
    priority=TaskPriority.LOW,
    max_retries=0,
    time_limit=SYNC_SECONDS * 1000,
)
async def sync() -> None:
    """Also sent once when the worker boots (see worker/scheduler.py), so a
    deploy across the hourly tick never leaves the chart empty."""
    if not counter.configured():
        log.info("visits.sync.unconfigured")
        return
    redis = create_redis("worker")
    stored: dict[str, int] = {}
    try:
        async with Locker(redis).lock(
            SYNC_LOCK, timeout=SYNC_SECONDS, blocking_timeout=0
        ):
            # One dimension at a time: a failure on the second keeps the
            # first's rows.
            for dimension in counter.DIMENSIONS:
                try:
                    rows = await counter.fetch_visits(dimension)
                except CounterError as exc:
                    log.warning(
                        "visits.sync.failed", dimension=dimension, error=str(exc)
                    )
                    continue
                try:
                    async with AsyncSessionMaker() as session:
                        stored[dimension] = await service.upsert(session, rows)
                        await session.commit()
                except SQLAlchemyError as exc:
                    # The session rolls back on the way out; the next
                    # dimension still gets its turn.
                    log.warning(
                        "visits.sync.store_failed", dimension=dimension, error=str(exc)
                    )
    except TimeoutLockError:
        log.debug("visits.sync.locked")
        return
    finally:
        await redis.close()
    log.info("visits.sync", **stored)
