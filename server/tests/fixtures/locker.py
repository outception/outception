import pytest_asyncio

from outception.locker import Locker
from outception.redis import Redis


@pytest_asyncio.fixture
async def locker(redis: Redis) -> Locker:
    return Locker(redis)
