"""One prune actor for everything the news domain accumulates: cluster
members after 14 days, scores after 30, briefings after 90, job runs
after 30, feedback after 180, rejected and withdrawn products after 90.
Daily, early, on the pipeline queue."""

from datetime import timedelta

import structlog
from sqlalchemy import Delete, delete

from outception.kit.utils import utc_now
from outception.models import (
    Feedback,
    JobRun,
    Launch,
    LaunchStatus,
    NewsBriefing,
    NewsCluster,
    NewsClusterMember,
    NewsClusterScore,
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
SCORE_DAYS = 30
BRIEFING_DAYS = 90
JOB_RUN_DAYS = 30
FEEDBACK_DAYS = 180
LAUNCH_DAYS = 90


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
    await run(
        "scores",
        delete(NewsClusterScore).where(
            NewsClusterScore.scored_at < now - timedelta(days=SCORE_DAYS)
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
        "briefings",
        delete(NewsBriefing).where(
            NewsBriefing.built_at < now - timedelta(days=BRIEFING_DAYS)
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
    return counts


@actor(
    actor_name="news.prune_briefing_data",
    cron_trigger=CronTrigger(hour=3, minute=30),
    queue_name=TaskQueue.NEWS_PIPELINE,
    priority=TaskPriority.LOW,
    max_retries=0,
    time_limit=10 * 60 * 1000,
)
async def prune_briefing_data() -> None:
    async with AsyncSessionMaker() as session:
        counts = await prune(session)
        await session.commit()
    log.info("news.prune_briefing_data", **counts)
