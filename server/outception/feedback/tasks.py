import structlog

from outception.worker import AsyncSessionMaker, CronTrigger, TaskPriority, actor

from . import service

log = structlog.get_logger()


@actor(
    actor_name="feedback.digest",
    cron_trigger=CronTrigger(hour=8, minute=0),
    priority=TaskPriority.LOW,
    max_retries=0,
)
async def digest() -> None:
    async with AsyncSessionMaker() as session:
        carried = await service.send_digest(session)
        await session.commit()
    log.info("feedback.digest", carried=carried)
