from collections.abc import AsyncIterator

import pytest_asyncio
from fakeredis import FakeAsyncRedis

from outception.redis import Redis


@pytest_asyncio.fixture(autouse=True)
async def redis() -> AsyncIterator[Redis]:
    yield FakeAsyncRedis()
