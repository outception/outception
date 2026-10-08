import asyncio

import pytest

from outception.net.provider import (
    FLIGHT_KEY,
    Fetched,
    ProviderError,
    ProviderSpec,
    Status,
    Toolkit,
    clamp_cooldown,
    interval_for_quota,
    parse_retry_after,
)
from outception.net.state import SignalState
from outception.redis import Redis

SPEC = ProviderSpec(
    id="tables-test",
    interval=60_000,
    fresh_for=60_000,
    stale_for=600_000,
    budget_per_day=3,
    cooldown_range=(30, 300),
)


def test_parse_retry_after() -> None:
    assert parse_retry_after("120") == 120.0
    assert parse_retry_after("Wed, 21 Oct 2015 07:28:00 GMT", now=1445412470.0) == 10.0
    assert parse_retry_after("garbage") is None
    assert parse_retry_after(None) is None


def test_clamp_cooldown() -> None:
    assert clamp_cooldown(SPEC, None) == 30
    assert clamp_cooldown(SPEC, 5) == 30
    assert clamp_cooldown(SPEC, 100) == 100
    assert clamp_cooldown(SPEC, 5000) == 300


def test_interval_for_quota() -> None:
    assert interval_for_quota(SPEC, 0.9) == 60_000
    assert interval_for_quota(SPEC, 0.3) == 120_000
    assert interval_for_quota(SPEC, 0.15) == 240_000
    assert interval_for_quota(SPEC, 0.0) == 720_000


@pytest.mark.asyncio
class TestFetch:
    async def test_serves_cached_within_interval(self, redis: Redis) -> None:
        toolkit = Toolkit(redis)
        calls = 0

        async def fetch() -> str:
            nonlocal calls
            calls += 1
            return "new"

        result = await toolkit.fetch(
            SPEC, "k", fetch, cached="old", cached_at=1000.0, now=1030.0
        )
        assert result == Fetched("old", SignalState.nominal, Status.cached, 1000.0)
        assert calls == 0

    async def test_refreshes_past_interval(self, redis: Redis) -> None:
        toolkit = Toolkit(redis)

        async def fetch() -> str:
            return "new"

        result = await toolkit.fetch(
            SPEC, "k", fetch, cached="old", cached_at=1000.0, now=1100.0
        )
        assert result.value == "new"
        assert result.state == SignalState.nominal
        assert result.status == Status.fresh
        assert await toolkit.budget_spent(SPEC.id, now=1100.0) == 1

    async def test_cooldown_on_429_serves_stale(self, redis: Redis) -> None:
        toolkit = Toolkit(redis)

        async def fetch() -> str:
            raise ProviderError("rate limited", status=429, retry_after=120)

        result = await toolkit.fetch(
            SPEC, "k", fetch, cached="old", cached_at=1000.0, now=1100.0
        )
        assert result.value == "old"
        assert result.state == SignalState.degraded
        assert result.status == Status.cooling
        assert 0 < await toolkit.cooldown_remaining(SPEC.id) <= 120

        calls = 0

        async def fetch_again() -> str:
            nonlocal calls
            calls += 1
            return "new"

        again = await toolkit.fetch(
            SPEC, "k", fetch_again, cached="old", cached_at=1000.0, now=1100.0
        )
        assert again.status == Status.cooling
        assert calls == 0

    async def test_budget_exhausted_serves_stale(self, redis: Redis) -> None:
        toolkit = Toolkit(redis)
        for _ in range(3):
            await toolkit.charge_budget(SPEC, now=1100.0)

        async def fetch() -> str:
            raise AssertionError("must not fetch over budget")

        result = await toolkit.fetch(
            SPEC, "k", fetch, cached="old", cached_at=1000.0, now=1100.0
        )
        assert result.status == Status.budget
        assert result.state == SignalState.stale

    async def test_negative_cache(self, redis: Redis) -> None:
        toolkit = Toolkit(redis)
        calls = 0

        async def fetch() -> str | None:
            nonlocal calls
            calls += 1
            return None

        first = await toolkit.fetch(
            SPEC, "k", fetch, cached=None, cached_at=None, now=1100.0
        )
        assert first.status == Status.negative
        assert first.state == SignalState.unavailable
        second = await toolkit.fetch(
            SPEC, "k", fetch, cached=None, cached_at=None, now=1101.0
        )
        assert second.status == Status.negative
        assert calls == 1

    async def test_timeout_retries_once(self, redis: Redis) -> None:
        toolkit = Toolkit(redis)
        calls = 0

        async def fetch() -> str:
            nonlocal calls
            calls += 1
            if calls == 1:
                raise ProviderError("timeout", timeout=True)
            return "new"

        result = await toolkit.fetch(
            SPEC, "k", fetch, cached=None, cached_at=None, now=1100.0
        )
        assert result.value == "new"
        assert calls == 2

    async def test_4xx_does_not_retry_or_cool(self, redis: Redis) -> None:
        toolkit = Toolkit(redis)
        calls = 0

        async def fetch() -> str:
            nonlocal calls
            calls += 1
            raise ProviderError("not found", status=404)

        result = await toolkit.fetch(
            SPEC, "k", fetch, cached="old", cached_at=1000.0, now=1100.0
        )
        assert result.status == Status.failed
        assert calls == 1
        assert await toolkit.cooldown_remaining(SPEC.id) == 0

    async def test_adaptive_interval(self, redis: Redis) -> None:
        toolkit = Toolkit(redis)
        await toolkit.note_quota(SPEC, 0.05)
        assert await toolkit.interval(SPEC) == 720_000


@pytest.mark.asyncio
class TestSingleFlight:
    async def test_release_leaves_another_holders_flight_alone(
        self, redis: Redis
    ) -> None:
        toolkit = Toolkit(redis)
        key = FLIGHT_KEY.format(key="k")

        async def work() -> str:
            # The TTL ran out mid-work and a second caller took the key.
            await redis.set(key, "someone-else")
            return "done"

        assert await toolkit.single_flight("k", work, timeout=5) == "done"
        assert await redis.get(key) == "someone-else"

    async def test_release_frees_its_own_flight(self, redis: Redis) -> None:
        toolkit = Toolkit(redis)

        async def work() -> str:
            return "done"

        await toolkit.single_flight("k", work, timeout=5)
        assert await redis.exists(FLIGHT_KEY.format(key="k")) == 0

    async def test_waiter_serves_what_the_holder_wrote(self, redis: Redis) -> None:
        toolkit = Toolkit(redis)
        store: dict[str, tuple[str | None, float | None]] = {"k": ("old", 1000.0)}
        await redis.set(FLIGHT_KEY.format(key="k"), "holder", ex=5)

        async def fetch() -> str:
            raise AssertionError("the waiter never fetches")

        async def reload() -> tuple[str | None, float | None]:
            return store["k"]

        async def holder_finishes() -> None:
            await asyncio.sleep(0.15)
            store["k"] = ("new", 1100.0)
            await redis.delete(FLIGHT_KEY.format(key="k"))

        asyncio.get_running_loop().create_task(holder_finishes())
        result = await toolkit.fetch(
            SPEC,
            "k",
            fetch,
            cached="old",
            cached_at=1000.0,
            now=1100.0,
            reload=reload,
        )
        assert result == Fetched("new", SignalState.nominal, Status.cached, 1100.0)
