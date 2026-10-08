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


@pytest.mark.asyncio
async def test_an_ipv6_host_cannot_rotate_into_a_fresh_allowance(
    redis: Redis,
) -> None:
    for n in range(3):
        assert await client_budget.spend(
            redis, "summary", f"2001:db8::{n + 1}", limit=2, window_seconds=60
        ) is (n < 2)
    # Another /64 is another household.
    assert await client_budget.spend(
        redis, "summary", "2001:db8:0:1::1", limit=2, window_seconds=60
    )


def test_networks_for_allowances() -> None:
    assert client_budget.client_network("203.0.113.9") == "203.0.113.9"
    assert client_budget.client_network("::ffff:203.0.113.9") == "203.0.113.9"
    assert client_budget.client_network("2001:db8::1") == "2001:db8::/64"
    assert client_budget.client_network("not an address") == "not an address"
