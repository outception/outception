import threading
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

from ._broker import scheduler_middleware
from ._health import _run_exposition_server, set_heartbeat_checker

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
    set_heartbeat_checker(_is_scheduler_healthy)
    health_thread = threading.Thread(target=_run_exposition_server, daemon=True)
    health_thread.start()

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
