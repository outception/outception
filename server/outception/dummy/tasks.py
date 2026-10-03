from typing import Annotated

from sqlalchemy import text

from outception.observability.task_logging import LoggableField
from outception.worker import AsyncSessionMaker, RedisMiddleware, TaskPriority, actor


@actor(actor_name="dummy", priority=TaskPriority.LOW)
async def dummy_task(
    *, redis_key: str = "dummy", failure: Annotated[bool, LoggableField] = False
) -> None:
    if failure:
        raise RuntimeError("Dummy task failure requested.")

    async with AsyncSessionMaker() as session:
        await session.execute(text("SELECT 1"))

    await RedisMiddleware.get().incr(redis_key)
