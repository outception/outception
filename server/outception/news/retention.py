"""One prune actor for everything the news domain accumulates: cluster
members after 14 days, job runs after 30, feedback after 180, rejected
and withdrawn products after 90. Daily, early, on the pipeline queue."""

from datetime import timedelta

import structlog
from sqlalchemy import Delete, delete

from outception.kit.utils import utc_now
from outception.models import (
    Feedback,
    JobRun,
    Launch,
    LaunchStatus,
    NewsCluster,
    NewsClusterMember,
    SiteVisit,
)
from outception.postgres import AsyncSession
from outception.worker import (
    AsyncSessionMaker,
    CronTrigger,
    TaskPriority,
    TaskQueue,
    actor,
)

log = structlog.get_logger()

MEMBER_DAYS = 14
JOB_RUN_DAYS = 30
FEEDBACK_DAYS = 180
LAUNCH_DAYS = 90
VISIT_DAYS = 90


async def prune(session: AsyncSession) -> dict[str, int]:
    now = utc_now()
    counts: dict[str, int] = {}

    async def run(name: str, statement: Delete) -> None:
        result = await session.execute(statement)
        counts[name] = int(getattr(result, "rowcount", 0) or 0)

    await run(
        "members",
        delete(NewsClusterMember).where(
            NewsClusterMember.seen_at < now - timedelta(days=MEMBER_DAYS)
        ),
    )
    # A cluster nobody has seen in the member window is gone with its
    # members.
    await run(
        "clusters",
        delete(NewsCluster).where(
            NewsCluster.last_seen_at < now - timedelta(days=MEMBER_DAYS)
        ),
    )
    await run(
        "job_runs",
        delete(JobRun).where(JobRun.started_at < now - timedelta(days=JOB_RUN_DAYS)),
    )
    await run(
        "feedback",
        delete(Feedback).where(
            Feedback.created_at < now - timedelta(days=FEEDBACK_DAYS)
        ),
    )
    await run(
        "launches",
        delete(Launch).where(
            Launch.state.in_((LaunchStatus.rejected, LaunchStatus.withdrawn)),
            Launch.created_at < now - timedelta(days=LAUNCH_DAYS),
        ),
    )
    await run(
        "visits",
        delete(SiteVisit).where(
            SiteVisit.day < (now - timedelta(days=VISIT_DAYS)).date()
        ),
    )
    return counts


@actor(
    actor_name="news.prune_pipeline_data",
    cron_trigger=CronTrigger(hour=3, minute=30),
    queue_name=TaskQueue.NEWS_PIPELINE,
    priority=TaskPriority.LOW,
    max_retries=0,
    time_limit=10 * 60 * 1000,
)
async def prune_pipeline_data() -> None:
    async with AsyncSessionMaker() as session:
        counts = await prune(session)
        await session.commit()
    log.info("news.prune_pipeline_data", **counts)
