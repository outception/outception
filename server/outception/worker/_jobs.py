"""Close the job runs a dead worker left open: anything still running
when a worker boots was interrupted, and must not read as in flight
forever."""

import asyncio

import dramatiq
import structlog

from outception.jobs import mark_interrupted
from outception.kit.db.postgres import create_async_sessionmaker
from outception.postgres import create_async_engine

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
        # Its own engine, disposed before `asyncio.run` closes this loop: a
        # connection from the shared pool would stay bound to the closed
        # loop and fail the first actor that checked it out ("Event loop is
        # closed" on the email log write, seen in a local run).
        engine = create_async_engine("worker", pool_logging_name="worker-boot")
        try:
            async with create_async_sessionmaker(engine)() as session:
                closed = await mark_interrupted(session)
                await session.commit()
        finally:
            await engine.dispose()
        return closed
