from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from outception.kit.utils import utc_now
from outception.models import (
    Feedback,
    JobKind,
    JobRun,
    JobState,
    NewsCluster,
    NewsClusterMember,
)
from outception.news.retention import prune
from outception.postgres import AsyncSession


async def _count(session: AsyncSession, model: type[object]) -> int:
    return int(await session.scalar(select(func.count()).select_from(model)) or 0)


def _cluster(age_days: int) -> NewsCluster:
    when = utc_now() - timedelta(days=age_days)
    return NewsCluster(
        key=f"key-{uuid4().hex}",
        title="t",
        first_seen_at=when,
        last_seen_at=when,
        lead_source_id="bbc-world",
    )


@pytest.mark.asyncio
async def test_prune_keeps_the_retention_windows(session: AsyncSession) -> None:
    fresh, old = _cluster(1), _cluster(20)
    session.add_all([fresh, old])
    await session.flush()
    now = utc_now()
    session.add_all(
        [
            NewsClusterMember(
                cluster_id=fresh.id,
                source_id="a",
                item_id="1",
                url="https://a/1",
                url_key="k1",
                title="t",
                seen_at=now - timedelta(days=1),
            ),
            NewsClusterMember(
                cluster_id=fresh.id,
                source_id="a",
                item_id="2",
                url="https://a/2",
                url_key="k2",
                title="t",
                seen_at=now - timedelta(days=15),
            ),
            JobRun(
                kind=JobKind.summary,
                subject="x",
                state=JobState.completed,
                lane="interactive",
                started_at=now - timedelta(days=31),
            ),
            Feedback(
                message="old", surface="web", created_at=now - timedelta(days=181)
            ),
            Feedback(message="new", surface="web"),
        ]
    )
    await session.flush()
    counts = await prune(session)
    assert counts == {
        "members": 1,
        "clusters": 1,
        "job_runs": 1,
        "feedback": 1,
        "launches": 0,
        "visits": 0,
    }
    assert await _count(session, NewsCluster) == 1
    assert await _count(session, NewsClusterMember) == 1
    assert await _count(session, JobRun) == 0
    assert await _count(session, Feedback) == 1
