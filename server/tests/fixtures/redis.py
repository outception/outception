from collections.abc import AsyncIterator

import pytest_asyncio
from fakeredis import FakeAsyncRedis

from outception.redis import Redis


@pytest_asyncio.fixture(autouse=True)
async def redis() -> AsyncIterator[Redis]:
    # decode_responses matches the production client: str in, str out.
    yield FakeAsyncRedis(decode_responses=True)
