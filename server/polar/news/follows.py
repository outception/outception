"""Followed-source data operations for the personalised wall."""

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from polar.kit.utils import generate_uuid, utc_now
from polar.models import UserFollowedSource
from polar.postgres import AsyncReadSession, AsyncSession
from polar.redis import Redis

from . import cache
from .metadata import SOURCES
from .schemas import NewsSearchItem


async def list_followed(session: AsyncReadSession, user_id: UUID) -> list[str]:
    result = await session.execute(
        select(UserFollowedSource.source_id).where(
            UserFollowedSource.user_id == user_id
        )
    )
    return [row[0] for row in result.all()]


async def follow(session: AsyncSession, user_id: UUID, source_id: str) -> None:
    """Idempotently follow a source. The insert upserts on the unique
    constraint, so concurrent double-follows collapse to a single row instead
    of racing a read-then-write and 500ing on the unique violation."""
    stmt = (
        pg_insert(UserFollowedSource)
        .values(
            id=generate_uuid(),
            created_at=utc_now(),
            user_id=user_id,
            source_id=source_id,
        )
        .on_conflict_do_nothing(constraint="uq_user_followed_source")
    )
    await session.execute(stmt)


async def unfollow(session: AsyncSession, user_id: UUID, source_id: str) -> None:
    await session.execute(
        delete(UserFollowedSource).where(
            UserFollowedSource.user_id == user_id,
            UserFollowedSource.source_id == source_id,
        )
    )


async def followed_feed(
    redis: Redis, source_ids: list[str], *, limit: int = 40
) -> list[NewsSearchItem]:
    """Merge cached headlines from the given sources into one freshest-first
    feed. Reads warm cache only (never fetches), so cold sources contribute
    nothing until the wall warms them."""
    hits: list[NewsSearchItem] = []
    for source_id in source_ids:
        entry = await cache.get(redis, source_id)
        if entry is None:
            continue
        source_name = str(SOURCES.get(source_id, {}).get("name", source_id))
        for item in entry.items:
            hits.append(
                NewsSearchItem(
                    source_id=source_id, source_name=source_name, item=item
                )
            )
    hits.sort(key=lambda h: h.item.pub_date or 0, reverse=True)
    return hits[:limit]
