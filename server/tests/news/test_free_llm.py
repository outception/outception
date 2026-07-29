import httpx
import pytest
from pytest_mock import MockerFixture

from outception.news import free_llm
from outception.redis import Redis


def _configure(mocker: MockerFixture, **overrides: str | None) -> None:
    defaults: dict[str, str | None] = {
        "GROQ_API_KEY": None,
        "GROQ_API_KEYS": None,
        "MISTRAL_API_KEY": None,
        "MISTRAL_API_KEYS": None,
    }
    defaults.update(overrides)
    for name, value in defaults.items():
        mocker.patch.object(free_llm.settings, name, value)


def _response(status: int, body: str = "", headers: dict[str, str] | None = None):
    request = httpx.Request("POST", "https://api.example.com")
    return httpx.Response(status, text=body, headers=headers or {}, request=request)


class TestEndpoints:
    def test_unconfigured_pool_is_empty(self, mocker: MockerFixture) -> None:
        _configure(mocker)
        assert free_llm.endpoints() == []
        assert not free_llm.configured()

    def test_comma_separated_keys_fan_out(self, mocker: MockerFixture) -> None:
        _configure(mocker, GROQ_API_KEYS="k1, k2", MISTRAL_API_KEY="m1")
        pool = free_llm.endpoints()
        assert [e.id for e in pool] == ["groq:0", "groq:1", "mistral:0"]
        assert {e.provider for e in pool} == {"groq", "mistral"}

    def test_endpoint_id_never_contains_the_key(self, mocker: MockerFixture) -> None:
        # Ids go into logs and Redis key names; the secret must not ride along.
        _configure(mocker, GROQ_API_KEY="gsk_secret_value")
        endpoint = free_llm.endpoints()[0]
        assert "gsk_secret_value" not in endpoint.id


@pytest.mark.asyncio
class TestAcquire:
    async def test_round_robins_and_meters(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        _configure(mocker, GROQ_API_KEYS="k1,k2")
        seen = set()
        for _ in range(2):
            endpoint = await free_llm.acquire(redis)
            assert endpoint is not None
            seen.add(endpoint.id)
        assert seen == {"groq:0", "groq:1"}

    async def test_minute_full_endpoint_is_skipped(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        _configure(mocker, GROQ_API_KEY="k1")
        mocker.patch.object(free_llm.settings, "GROQ_RPM_CAP", 1)
        assert await free_llm.acquire(redis) is not None
        assert await free_llm.acquire(redis) is None

    async def test_benched_endpoint_is_skipped(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        _configure(mocker, GROQ_API_KEY="k1")
        endpoint = free_llm.endpoints()[0]
        await free_llm.note_failure(
            redis, endpoint, _make_429("rate limit, retry soon")
        )
        assert await free_llm.acquire(redis) is None
        assert not await free_llm.available(redis)


def _make_429(
    body: str, headers: dict[str, str] | None = None
) -> httpx.HTTPStatusError:
    response = _response(429, body, headers)
    return httpx.HTTPStatusError("429", request=response.request, response=response)


class TestCooldowns:
    def test_burst_429_benches_briefly(self) -> None:
        assert free_llm.cooldown_seconds(_make_429("slow down")) == 30

    def test_retry_after_header_wins(self) -> None:
        assert free_llm.cooldown_seconds(_make_429("x", {"retry-after": "17"})) == 17

    def test_daily_quota_benches_long(self) -> None:
        seconds = free_llm.cooldown_seconds(_make_429("Rate limit: RPD exceeded"))
        assert seconds is not None
        assert seconds > 60

    def test_payment_required_is_a_dead_key(self) -> None:
        # Cerebras answers this on accounts with no free tier: retrying it
        # all day is pure waste, so it benches like a revoked key.
        response = _response(402, "Payment required to access this resource.")
        exc = httpx.HTTPStatusError("402", request=response.request, response=response)
        assert free_llm.cooldown_seconds(exc) == 60 * 60

    def test_unparsable_reply_is_not_benched(self) -> None:
        assert free_llm.cooldown_seconds(ValueError("bad json")) is None
