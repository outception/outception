"""Followed-source data operations for the personalised wall."""

from uuid import UUID

from sqlalchemy import delete, select

from polar.models import UserFollowedSource
from polar.postgres import AsyncReadSession, AsyncSession


async def list_followed(session: AsyncReadSession, user_id: UUID) -> list[str]:
    result = await session.execute(
        select(UserFollowedSource.source_id).where(
            UserFollowedSource.user_id == user_id
        )
    )
    return [row[0] for row in result.all()]


async def follow(session: AsyncSession, user_id: UUID, source_id: str) -> None:
    """Idempotently follow a source (the unique constraint also guards races)."""
    existing = await session.execute(
        select(UserFollowedSource).where(
            UserFollowedSource.user_id == user_id,
            UserFollowedSource.source_id == source_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        return
    session.add(UserFollowedSource(user_id=user_id, source_id=source_id))
    await session.flush()


async def unfollow(session: AsyncSession, user_id: UUID, source_id: str) -> None:
    await session.execute(
        delete(UserFollowedSource).where(
            UserFollowedSource.user_id == user_id,
            UserFollowedSource.source_id == source_id,
        )
    )
