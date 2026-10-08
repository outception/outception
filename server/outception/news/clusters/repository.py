"""Postgres operations over the cluster tables."""

from collections.abc import Sequence
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from outception.kit.utils import generate_uuid, utc_now
from outception.models import NewsCluster, NewsClusterMember
from outception.postgres import AsyncSession


async def get(session: AsyncSession, cluster_id: UUID) -> NewsCluster | None:
    return await session.get(NewsCluster, cluster_id)


async def by_key(session: AsyncSession, key: str) -> NewsCluster | None:
    return await session.scalar(select(NewsCluster).where(NewsCluster.key == key))


async def by_member_url_key(session: AsyncSession, url_key: str) -> UUID | None:
    return await session.scalar(
        select(NewsClusterMember.cluster_id)
        .where(NewsClusterMember.url_key == url_key)
        .limit(1)
    )


async def create(
    session: AsyncSession,
    *,
    key: str,
    title: str,
    lead_source_id: str,
    seen_at: datetime | None = None,
) -> NewsCluster:
    seen_at = seen_at or utc_now()
    cluster = NewsCluster(
        id=generate_uuid(),
        key=key,
        title=title,
        first_seen_at=seen_at,
        last_seen_at=seen_at,
        publisher_count=0,
        member_count=0,
        lead_source_id=lead_source_id,
    )
    session.add(cluster)
    await session.flush()
    return cluster


async def add_member(
    session: AsyncSession,
    cluster_id: UUID,
    *,
    source_id: str,
    item_id: str,
    url: str,
    url_key: str,
    title: str,
    pub_date: datetime | None,
    seen_at: datetime | None = None,
) -> bool:
    """Idempotent: the same item from the same source joins once. Returns
    whether a row was added."""
    statement = (
        pg_insert(NewsClusterMember)
        .values(
            cluster_id=cluster_id,
            source_id=source_id,
            item_id=item_id[:2048],
            url=url,
            url_key=url_key,
            title=title,
            pub_date=pub_date,
            seen_at=seen_at or utc_now(),
        )
        .on_conflict_do_nothing(index_elements=["cluster_id", "source_id", "item_id"])
    )
    result = await session.execute(statement)
    return bool(getattr(result, "rowcount", 0))


async def recount(session: AsyncSession, cluster_id: UUID) -> tuple[int, int]:
    """Refresh the member and publisher counts and the last-seen stamp;
    returns (publisher_count, member_count)."""
    row = (
        await session.execute(
            select(
                func.count(func.distinct(NewsClusterMember.source_id)),
                func.count(),
                func.max(NewsClusterMember.seen_at),
            ).where(NewsClusterMember.cluster_id == cluster_id)
        )
    ).one()
    publishers, members, last_seen = int(row[0]), int(row[1]), row[2]
    await session.execute(
        update(NewsCluster)
        .where(NewsCluster.id == cluster_id)
        .values(
            publisher_count=publishers,
            member_count=members,
            last_seen_at=last_seen or utc_now(),
        )
    )
    return publishers, members


async def members(
    session: AsyncSession, cluster_id: UUID
) -> Sequence[NewsClusterMember]:
    result = await session.execute(
        select(NewsClusterMember)
        .where(NewsClusterMember.cluster_id == cluster_id)
        .order_by(NewsClusterMember.seen_at)
    )
    return result.scalars().all()


async def move_members(session: AsyncSession, from_id: UUID, to_id: UUID) -> int:
    """Merge: every member of `from_id` joins `to_id` (duplicates by
    source and item are dropped), then the empty cluster goes."""
    moved = 0
    for member in await members(session, from_id):
        added = await add_member(
            session,
            to_id,
            source_id=member.source_id,
            item_id=member.item_id,
            url=member.url,
            url_key=member.url_key,
            title=member.title,
            pub_date=member.pub_date,
            seen_at=member.seen_at,
        )
        moved += int(added)
    source = await get(session, from_id)
    target = await get(session, to_id)
    if source is not None and target is not None:
        target.first_seen_at = min(target.first_seen_at, source.first_seen_at)
        await session.delete(source)
    await session.flush()
    await recount(session, to_id)
    return moved


async def recent(
    session: AsyncSession, *, hours: int = 24, min_publishers: int = 1
) -> Sequence[NewsCluster]:
    since = utc_now() - timedelta(hours=hours)
    result = await session.execute(
        select(NewsCluster)
        .where(
            NewsCluster.last_seen_at >= since,
            NewsCluster.publisher_count >= min_publishers,
        )
        .order_by(NewsCluster.last_seen_at.desc())
    )
    return result.scalars().all()
