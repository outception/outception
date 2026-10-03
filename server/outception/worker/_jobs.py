"""Close the job runs a dead worker left open: anything still running
when a worker boots was interrupted, and must not read as in flight
forever."""

import asyncio

import dramatiq
import structlog

from outception.jobs import mark_interrupted

from ._sqlalchemy import AsyncSessionMaker

log: structlog.stdlib.BoundLogger = structlog.get_logger()


class JobRunsMiddleware(dramatiq.Middleware):
    def after_worker_boot(
        self, broker: dramatiq.Broker, worker: dramatiq.Worker
    ) -> None:
        try:
            closed = asyncio.run(self._close_interrupted())
        except Exception as error:
            log.warning("jobs.interrupted_sweep_failed", error=str(error))
            return
        if closed:
            log.info("jobs.interrupted_closed", count=closed)

    @staticmethod
    async def _close_interrupted() -> int:
        async with AsyncSessionMaker() as session:
            closed = await mark_interrupted(session)
            await session.commit()
        return closed
