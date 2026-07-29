"""Followed-source data operations for the personalised wall."""

from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from outception.exceptions import OutceptionError
from outception.kit.utils import generate_uuid, utc_now
from outception.models import UserFollowedSource
from outception.postgres import AsyncReadSession, AsyncSession
from outception.redis import Redis

from . import cache
from .metadata import SOURCES
from .schemas import NewsSearchItem
from .search import _MGET_CHUNK, _chunks

# Far above any real reader (the whole roster is ~8,000 sources) but low
# enough that a scripted account can't grow an unbounded row set — and an
# unbounded followed-feed MGET fan-out — one PUT at a time.
MAX_FOLLOWED_SOURCES = 500


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
    # The count excludes this source so a re-follow at the cap stays
    # idempotent (204) instead of 422ing on a row it wouldn't add.
    count = await session.scalar(
        select(func.count())
        .select_from(UserFollowedSource)
        .where(
            UserFollowedSource.user_id == user_id,
            UserFollowedSource.source_id != source_id,
        )
    )
    if count is not None and count >= MAX_FOLLOWED_SOURCES:
        raise OutceptionError(
            f"You can follow at most {MAX_FOLLOWED_SOURCES} sources",
            status_code=422,
        )
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
    # MGET per chunk rather than per source — a per-source GET loop costs a
    # Redis round trip per follow (100 follows = 100 serial RTTs) — but
    # chunked like search so one maxed-out follow set can't hold a single
    # giant MGET on Redis' hot path.
    for chunk in _chunks(source_ids, _MGET_CHUNK):
        for source_id, raw in await cache.mget_hot_raw(redis, chunk):
            entry = cache.parse_entry(raw)
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
