import pytest

from outception.config import settings
from outception.news.summaries.providers.governor import (
    CapExceeded,
    Governor,
    LaneDisabled,
)
from outception.news.summaries.providers.lanes import (
    Consumer,
    Lane,
    warmer_should_stand_down,
)
from outception.redis import Redis

NOW = 1_700_000_000.0


@pytest.fixture
def small_caps(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "LLM_INTERACTIVE_HOURLY_CAP", 5)
    monkeypatch.setattr(settings, "LLM_INTERACTIVE_DAILY_CAP", 8)
    monkeypatch.setattr(settings, "LLM_BACKGROUND_HOURLY_CAP", 5)
    monkeypatch.setattr(settings, "LLM_BACKGROUND_DAILY_CAP", 8)
    monkeypatch.setattr(settings, "LLM_GLOBAL_HOURLY_CAP", 7)
    monkeypatch.setattr(settings, "LLM_PAID_DAILY_CAP", 2)
    monkeypatch.setattr(settings, "LLM_BACKGROUND_SUBCAP_RESOLVE", 3)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "k")
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "k")


@pytest.mark.asyncio
@pytest.mark.usefixtures("small_caps")
class TestReserveSettle:
    async def test_reserve_charges_three_counters(self, redis: Redis) -> None:
        governor = Governor(redis)
        reservation = await governor.reserve(Lane.interactive, "gemini", 2, now=NOW)
        assert reservation.units == 2
        assert await governor.used(Lane.interactive, now=NOW) == (2, 2)
        assert await redis.exists(f"llm:reserve:{reservation.call_id}")

    async def test_settle_charges_the_difference(self, redis: Redis) -> None:
        governor = Governor(redis)
        reservation = await governor.reserve(Lane.interactive, "gemini", 2, now=NOW)
        await governor.settle(reservation, 4, now=NOW)
        assert await governor.used(Lane.interactive, now=NOW) == (4, 4)
        assert not await redis.exists(f"llm:reserve:{reservation.call_id}")

    async def test_settle_at_zero_refunds(self, redis: Redis) -> None:
        governor = Governor(redis)
        reservation = await governor.reserve(Lane.interactive, "gemini", 3, now=NOW)
        await governor.settle(reservation, 0, now=NOW)
        assert await governor.used(Lane.interactive, now=NOW) == (0, 0)

    async def test_lane_hourly_cap(self, redis: Redis) -> None:
        governor = Governor(redis)
        await governor.reserve(Lane.interactive, "gemini", 5, now=NOW)
        with pytest.raises(CapExceeded):
            await governor.reserve(Lane.interactive, "gemini", 1, now=NOW)

    async def test_global_cap_spans_lanes(self, redis: Redis) -> None:
        governor = Governor(redis)
        await governor.reserve(Lane.interactive, "gemini", 4, now=NOW)
        await governor.reserve(Lane.background, "gemini", 3, now=NOW)
        with pytest.raises(CapExceeded):
            await governor.reserve(Lane.background, "gemini", 1, now=NOW)

    async def test_background_sub_cap(self, redis: Redis) -> None:
        governor = Governor(redis)
        await governor.reserve(
            Lane.background, "gemini", 3, consumer=Consumer.resolve, now=NOW
        )
        with pytest.raises(CapExceeded) as excinfo:
            await governor.reserve(
                Lane.background, "gemini", 1, consumer=Consumer.resolve, now=NOW
            )
        assert "resolve sub" in str(excinfo.value)

    async def test_paid_daily_cap(self, redis: Redis) -> None:
        governor = Governor(redis)
        await governor.reserve(Lane.interactive, "paid", 2, now=NOW)
        with pytest.raises(CapExceeded):
            await governor.reserve(Lane.interactive, "paid", 1, now=NOW)

    async def test_kill_switch(
        self, redis: Redis, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "LLM_DISABLED", True)
        governor = Governor(redis)
        with pytest.raises(LaneDisabled):
            await governor.reserve(Lane.interactive, "gemini", 1, now=NOW)
        assert await governor.available("gemini") is False


@pytest.mark.asyncio
@pytest.mark.usefixtures("small_caps")
class TestAvailability:
    async def test_cooldown_and_disable(self, redis: Redis) -> None:
        governor = Governor(redis)
        assert await governor.available("gemini") is True
        assert await governor.available("groq") is False  # no key
        seconds = await governor.cool_down("gemini", 60)
        assert seconds == 60
        assert await governor.available("gemini") is False
        await governor.clear_cooldown("gemini") if hasattr(
            governor, "clear_cooldown"
        ) else await redis.delete("net:cooldown:gemini")
        await governor.disable("gemini")
        assert await governor.available("gemini") is False
        await governor.enable("gemini")
        assert await governor.available("gemini") is True

    async def test_served_record(self, redis: Redis) -> None:
        governor = Governor(redis)
        await governor.record_served("abc", "gemini-x")
        assert await governor.served("abc") == "gemini-x"


def test_warmer_stands_down(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "LLM_INTERACTIVE_DAILY_CAP", 100)
    assert warmer_should_stand_down(49) is False
    assert warmer_should_stand_down(50) is True
