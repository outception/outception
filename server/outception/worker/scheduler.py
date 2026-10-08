import time

import logfire
import structlog
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.base import STATE_STOPPED
from apscheduler.schedulers.blocking import BlockingScheduler

from outception import tasks
from outception.logfire import configure_logfire
from outception.logging import Logger
from outception.logging import configure as configure_logging
from outception.redis import SyncRedis, create_sync_redis
from outception.sentry import configure_sentry
from outception.worker import broker

from ._broker import scheduler_middleware
from ._health import set_heartbeat_checker

configure_sentry()
configure_logfire("worker")
configure_logging(logfire=True)

log: Logger = structlog.get_logger()

# The heartbeat goes through Redis as well as a module global: the scheduler
# and the API's /health live in different processes, so only a shared key
# lets the API notice a wedged scheduler.
SCHEDULER_HEARTBEAT_KEY = "worker:scheduler:heartbeat"
HEARTBEAT_STALENESS_SECONDS = 60
# Cap the idle sleep below the staleness threshold so an idle scheduler keeps
# refreshing its heartbeat instead of reading as unhealthy.
HEARTBEAT_INTERVAL_SECONDS = 30
_last_heartbeat: float = 0.0


def _bounded_wait_seconds(wait_seconds: float | None) -> float:
    if wait_seconds is None:
        return HEARTBEAT_INTERVAL_SECONDS
    return min(wait_seconds, HEARTBEAT_INTERVAL_SECONDS)


def publish_heartbeat(redis: SyncRedis, now: float | None = None) -> None:
    try:
        redis.set(
            SCHEDULER_HEARTBEAT_KEY,
            str(time.time() if now is None else now),
            ex=HEARTBEAT_STALENESS_SECONDS * 5,
        )
    except Exception:
        log.warning("scheduler.heartbeat_publish_failed")


class LogfireBlockingScheduler(BlockingScheduler):
    def __init__(self, redis: SyncRedis) -> None:
        super().__init__()
        self._redis = redis

    def _main_loop(self) -> None:
        global _last_heartbeat
        wait_seconds: float | None = 1
        while self.state != STATE_STOPPED:
            with logfire.span("Scheduler wakeup"):
                self._event.wait(_bounded_wait_seconds(wait_seconds))
                self._event.clear()
                wait_seconds = self._process_jobs()
                _last_heartbeat = time.monotonic()
                publish_heartbeat(self._redis)


def _is_scheduler_healthy() -> bool:
    if _last_heartbeat == 0.0:
        return True
    return (time.monotonic() - _last_heartbeat) < HEARTBEAT_STALENESS_SECONDS


def start() -> None:
    # The heartbeat the API reads lives in Redis (publish_heartbeat); the
    # worker's own health server is forked once by HealthMiddleware in this
    # same process group, so the scheduler must not bind a second one on the
    # same port. (A second binder lost the race and logged "address already
    # in use" at every boot.)
    set_heartbeat_checker(_is_scheduler_healthy)

    scheduler = LogfireBlockingScheduler(create_sync_redis("worker"))

    scheduler.add_jobstore(MemoryJobStore(), "memory")

    for func, cron_trigger in scheduler_middleware.cron_triggers:
        scheduler.add_job(func, cron_trigger, jobstore="memory")

    # The visits sync also runs once at boot: a deploy that restarts the
    # worker across its hourly tick would otherwise leave the founder's
    # chart empty until the next one.
    try:
        broker.get_actor("visits.sync").send()
    except Exception as exc:
        log.warning("scheduler.boot_send_failed", actor="visits.sync", error=str(exc))

    try:
        scheduler.start()
    except KeyboardInterrupt:
        scheduler.shutdown()


__all__ = ["start", "tasks"]


if __name__ == "__main__":
    start()
