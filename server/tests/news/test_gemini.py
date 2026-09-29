import pytest
from pytest_mock import MockerFixture

from outception.config import settings
from outception.news import gemini
from outception.redis import Redis


@pytest.mark.asyncio
class TestRoundRobin:
    async def test_spreads_across_keys(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "GEMINI_API_KEYS", "ka,kb,kc")
        picked = set()
        for _ in range(6):
            slot = await gemini.acquire(redis, per_minute=100)
            assert slot is not None
            picked.add(slot[0])
        assert picked == {0, 1, 2}

    async def test_benched_key_skipped_in_rotation(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "GEMINI_API_KEYS", "ka,kb")
        await redis.set(gemini._COOLDOWN_KEY.format(i=0), "1", ex=60)
        for _ in range(4):
            slot = await gemini.acquire(redis, per_minute=100)
            assert slot is not None
            assert slot[0] == 1

    async def test_none_when_all_benched(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "GEMINI_API_KEYS", "ka,kb")
        for i in (0, 1):
            await redis.set(gemini._COOLDOWN_KEY.format(i=i), "1", ex=60)
        assert await gemini.acquire(redis, per_minute=100) is None
