import time

import logfire
import structlog
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.base import STATE_STOPPED
from apscheduler.schedulers.blocking import BlockingScheduler
from redis import Redis as SyncRedis

from outception import tasks
from outception.logfire import configure_logfire
from outception.logging import configure as configure_logging
from outception.redis import create_sync_redis
from outception.sentry import configure_sentry

from ._broker import scheduler_middleware
from ._health import HEARTBEAT_STALENESS_SECONDS, SCHEDULER_HEARTBEAT_KEY

log = structlog.get_logger()

configure_sentry()
configure_logfire("worker")
configure_logging(logfire=True)


# The heartbeat goes through Redis, not a module global. The scheduler and the
# health endpoint live in DIFFERENT processes (the endpoint is served from the
# broker's fork), so an in-process checker registered here was never consulted
# by the process that answers /healthz — a wedged scheduler, which silently
# stops every cron actor, reported healthy forever. Both exposition servers also
# bound the same port, so the scheduler's copy died on EADDRINUSE unnoticed.
def _publish_heartbeat(redis: "SyncRedis[str]") -> None:
    try:
        redis.set(
            SCHEDULER_HEARTBEAT_KEY,
            str(time.time()),
            ex=HEARTBEAT_STALENESS_SECONDS * 5,
        )
    except Exception:
        log.warning("scheduler.heartbeat_publish_failed")


class LogfireBlockingScheduler(BlockingScheduler):
    def __init__(self, redis: "SyncRedis[str]") -> None:
        super().__init__()
        self._redis = redis

    def _main_loop(self) -> None:
        wait_seconds = 1
        while self.state != STATE_STOPPED:
            with logfire.span("Scheduler wakeup"):
                self._event.wait(wait_seconds)
                self._event.clear()
                wait_seconds = self._process_jobs()
                _publish_heartbeat(self._redis)


def start() -> None:

    scheduler = LogfireBlockingScheduler(create_sync_redis("worker"))

    scheduler.add_jobstore(MemoryJobStore(), "memory")

    for func, cron_trigger in scheduler_middleware.cron_triggers:
        scheduler.add_job(func, cron_trigger, jobstore="memory")

    try:
        scheduler.start()
    except KeyboardInterrupt:
        scheduler.shutdown()


__all__ = ["start", "tasks"]


if __name__ == "__main__":
    start()
