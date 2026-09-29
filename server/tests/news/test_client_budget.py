import pytest

from outception.news import client_budget
from outception.redis import Redis


@pytest.mark.asyncio
class TestClientBudget:
    async def test_allows_up_to_the_limit_then_refuses(self, redis: Redis) -> None:
        for _ in range(3):
            assert await client_budget.spend(
                redis, "b", "1.2.3.4", limit=3, window_seconds=60
            )
        assert not await client_budget.spend(
            redis, "b", "1.2.3.4", limit=3, window_seconds=60
        )

    async def test_one_client_cannot_spend_anothers_allowance(
        self, redis: Redis
    ) -> None:
        """The whole point: the shared resource behind these routes is global,
        so a single caller must not be able to exhaust it for everyone."""
        for _ in range(3):
            await client_budget.spend(redis, "b", "1.2.3.4", limit=3, window_seconds=60)
        assert await client_budget.spend(
            redis, "b", "5.6.7.8", limit=3, window_seconds=60
        )

    async def test_buckets_are_independent(self, redis: Redis) -> None:
        await client_budget.spend(
            redis, "weather", "1.2.3.4", limit=1, window_seconds=60
        )
        assert await client_budget.spend(
            redis, "latest", "1.2.3.4", limit=1, window_seconds=60
        )

    async def test_fails_open_for_an_unidentified_caller(self, redis: Redis) -> None:
        """A header we failed to parse must degrade to the old behaviour, not
        to a blanket refusal that would take out readers behind a proxy."""
        for _ in range(10):
            assert await client_budget.spend(
                redis, "b", None, limit=1, window_seconds=60
            )

    async def test_the_window_expires(self, redis: Redis) -> None:
        await client_budget.spend(redis, "b", "1.2.3.4", limit=1, window_seconds=60)
        ttl = await redis.ttl("news:clientbudget:b:1.2.3.4:60")
        assert 0 < ttl <= 60
