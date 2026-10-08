"""The ops path deletes a reader with one SQL statement; every row of
theirs must cascade and nothing of theirs may hold the delete back."""

import pytest
from sqlalchemy import delete, select

from outception.models import OAuth2Client, User, UserFollowedSource
from outception.postgres import AsyncSession
from tests.fixtures.database import SaveFixture


@pytest.mark.asyncio
async def test_a_client_outlives_its_deleted_owner(
    session: AsyncSession, save_fixture: SaveFixture, user: User
) -> None:
    await save_fixture(UserFollowedSource(user_id=user.id, source_id="bbc-world"))
    client = OAuth2Client(client_id="owned-client", user=user)
    await save_fixture(client)

    await session.execute(delete(User).where(User.id == user.id))
    await session.flush()
    # Read back through fresh statements: the identity map still holds the
    # deleted objects and refreshing them lazily is not allowed here.
    session.expunge_all()

    gone = await session.execute(select(User.id).where(User.id == user.id))
    assert gone.scalar_one_or_none() is None
    follows = await session.execute(
        select(UserFollowedSource.id).where(UserFollowedSource.user_id == user.id)
    )
    assert follows.scalars().all() == []
    owner = await session.execute(
        select(OAuth2Client.user_id).where(OAuth2Client.id == client.id)
    )
    assert owner.scalar_one() is None
