import pytest
from pytest_mock import MockerFixture

from outception.news.summaries.providers.pool import (
    COOLDOWN_KEY,
    REJECTED_KEY,
    RPM_KEY,
    KeyPool,
    seconds_until_reset,
)
from outception.redis import Redis


async def _counter(redis: Redis, key: str) -> int:
    return int(await redis.get(key) or 0)


@pytest.mark.asyncio
class TestAcquire:
    async def test_spreads_across_keys(self, redis: Redis) -> None:
        pool = KeyPool(redis, "p", ["ka", "kb", "kc"], rpm=100)
        picked = set()
        for _ in range(6):
            slot = await pool.acquire()
            assert slot is not None
            picked.add(slot.index)
        assert picked == {0, 1, 2}

    async def test_benched_key_skipped_in_rotation(self, redis: Redis) -> None:
        pool = KeyPool(redis, "p", ["ka", "kb"], rpm=100)
        await redis.set(COOLDOWN_KEY.format(provider="p", i=0), "1", ex=60)
        for _ in range(4):
            slot = await pool.acquire()
            assert slot is not None
            assert slot.index == 1

    async def test_none_when_all_benched(self, redis: Redis) -> None:
        pool = KeyPool(redis, "p", ["ka", "kb"], rpm=100)
        for i in (0, 1):
            await pool.bench(i, 60)
        assert await pool.acquire() is None
        assert not await pool.available()

    async def test_minute_full_key_is_skipped(self, redis: Redis) -> None:
        pool = KeyPool(redis, "p", ["ka"], rpm=1)
        assert await pool.acquire() is not None
        assert await pool.acquire() is None
        # The probe never inflates a full key's meter.
        minute_keys = await redis.keys(RPM_KEY.format(provider="p", i=0, minute="*"))
        assert [await _counter(redis, k) for k in minute_keys] == [1]

    async def test_daily_ceiling_holds_the_free_tier(self, redis: Redis) -> None:
        pool = KeyPool(redis, "p", ["ka"], rpm=100, rpd=2)
        assert await pool.acquire() is not None
        assert await pool.acquire() is not None
        # Third of the day: refused, and the minute meter was handed back.
        assert await pool.acquire() is None
        minute_keys = await redis.keys(RPM_KEY.format(provider="p", i=0, minute="*"))
        assert [await _counter(redis, k) for k in minute_keys] == [2]

    async def test_unconfigured_pool_serves_nothing(self, redis: Redis) -> None:
        pool = KeyPool(redis, "p", [], rpm=10)
        assert not pool.configured
        assert await pool.acquire() is None
        assert not await pool.available()

    async def test_slot_repr_hides_the_key(self, redis: Redis) -> None:
        pool = KeyPool(redis, "p", ["gsk_secret_value"], rpm=10)
        slot = await pool.acquire()
        assert slot is not None
        assert "gsk_secret_value" not in repr(slot)


@pytest.mark.asyncio
class TestFailures:
    async def test_bench_for_the_implied_seconds(self, redis: Redis) -> None:
        pool = KeyPool(redis, "p", ["ka"], rpm=10)
        assert await pool.note_failure(0, 30) == 30
        assert await redis.ttl(COOLDOWN_KEY.format(provider="p", i=0)) > 0

    async def test_nothing_about_capacity_benches_nothing(self, redis: Redis) -> None:
        pool = KeyPool(redis, "p", ["ka"], rpm=10)
        assert await pool.note_failure(0, None) is None
        assert await pool.available()

    async def test_rejected_key_escalates_on_the_repeat(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        pool = KeyPool(redis, "p", ["ka"], rpm=10, reset_hour_utc=8)
        first = await pool.note_failure(0, 3600, rejected=True)
        assert first == 3600
        second = await pool.note_failure(0, 3600, rejected=True)
        assert second == seconds_until_reset(8)
        assert await _counter(redis, REJECTED_KEY.format(provider="p", i=0)) == 2


def test_seconds_until_reset_wraps_to_tomorrow() -> None:
    from datetime import UTC, datetime

    now = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
    assert seconds_until_reset(8, now) == 23 * 3600
    assert seconds_until_reset(10, now) == 3600
