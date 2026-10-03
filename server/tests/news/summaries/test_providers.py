import httpx
import pytest
from pytest_mock import MockerFixture

from outception.config import settings
from outception.news.summaries.providers.classes import ErrorClass, KeyBenched
from outception.news.summaries.providers.discipline import FIRST_LINE, OPENAI_STYLE
from outception.news.summaries.providers.gemini import GeminiProvider
from outception.news.summaries.providers.governor import CAP_PAID_DAY
from outception.news.summaries.providers.lanes import Lane
from outception.news.summaries.providers.openai_compatible import OpenAICompatible
from outception.news.summaries.providers.pool import COOLDOWN_KEY, KeyPool
from outception.news.summaries.providers.registry import (
    any_configured,
    build_chains,
    build_providers,
    free_configured,
)
from outception.redis import Redis


def _configure(mocker: MockerFixture, **overrides: str | None) -> None:
    defaults: dict[str, str | None] = {
        "GEMINI_API_KEY": None,
        "GEMINI_API_KEYS": None,
        "GROQ_API_KEY": None,
        "GROQ_API_KEYS": None,
        "MISTRAL_API_KEY": None,
        "MISTRAL_API_KEYS": None,
        "NVIDIA_API_KEY": None,
        "NVIDIA_API_KEYS": None,
        "OLLAMA_API_KEY": None,
        "OLLAMA_API_KEYS": None,
        "CLOUDFLARE_ACCOUNT_ID": None,
        "CLOUDFLARE_AI_TOKEN": None,
        "CLOUDFLARE_AI_TOKENS": None,
        "ANTHROPIC_API_KEY": None,
        "OWN_GENERATION_URL": None,
    }
    defaults.update(overrides)
    for name, value in defaults.items():
        mocker.patch.object(settings, name, value)


def _response(
    status: int, body: str = "", headers: dict[str, str] | None = None
) -> httpx.Response:
    request = httpx.Request("POST", "https://api.example.com")
    return httpx.Response(status, text=body, headers=headers or {}, request=request)


def _status_error(
    status: int, body: str = "", headers: dict[str, str] | None = None
) -> httpx.HTTPStatusError:
    response = _response(status, body, headers)
    return httpx.HTTPStatusError(
        str(status), request=response.request, response=response
    )


class TestRegistry:
    def test_unconfigured_pool_is_empty(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        _configure(mocker)
        assert build_providers(redis) == {}
        assert not free_configured()
        assert not any_configured()

    def test_comma_separated_keys_fan_out(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        _configure(
            mocker,
            GROQ_API_KEYS="k1, k2",
            MISTRAL_API_KEY="m1",
            NVIDIA_API_KEY="n1",
            OLLAMA_API_KEY="o1",
        )
        providers = build_providers(redis)
        assert list(providers) == ["groq", "mistral", "nvidia", "ollama"]
        groq = providers["groq"]
        assert isinstance(groq, OpenAICompatible)
        assert len(groq.pool) == 2
        nvidia = providers["nvidia"]
        assert isinstance(nvidia, OpenAICompatible)
        assert nvidia.url.startswith("https://integrate.api.nvidia.com/")
        assert nvidia.model == settings.NVIDIA_MODEL
        assert free_configured()

    def test_cloudflare_needs_the_account_id(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        _configure(mocker, CLOUDFLARE_AI_TOKEN="cf1")
        assert build_providers(redis) == {}
        assert not free_configured()
        _configure(mocker, CLOUDFLARE_AI_TOKEN="cf1", CLOUDFLARE_ACCOUNT_ID="abc123")
        (provider,) = build_providers(redis).values()
        assert isinstance(provider, OpenAICompatible)
        assert provider.id == "cloudflare"
        assert provider.url == (
            "https://api.cloudflare.com/client/v4/accounts/abc123/ai/v1/chat/completions"
        )
        assert provider.pool.rpd == settings.CLOUDFLARE_DAILY_CAP

    def test_paid_is_not_free(self, redis: Redis, mocker: MockerFixture) -> None:
        _configure(mocker, ANTHROPIC_API_KEY="k")
        assert list(build_providers(redis)) == ["paid"]
        assert not free_configured()
        assert any_configured()

    def test_own_generation_endpoint_joins(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        _configure(mocker, OWN_GENERATION_URL="http://engine:8100/v1/chat/completions")
        providers = build_providers(redis)
        assert list(providers) == ["own"]
        assert any_configured()


class TestDiscipline:
    def test_burst_429_benches_briefly(self) -> None:
        assert OPENAI_STYLE.cooldown_seconds(_status_error(429, "slow down")) == 30
        assert OPENAI_STYLE.classify(_status_error(429)) == ErrorClass.quota

    def test_retry_after_header_wins(self) -> None:
        exc = _status_error(429, "x", {"retry-after": "17"})
        assert OPENAI_STYLE.cooldown_seconds(exc) == 17

    def test_daily_quota_benches_long(self) -> None:
        seconds = OPENAI_STYLE.cooldown_seconds(
            _status_error(429, "Rate limit: RPD exceeded")
        )
        assert seconds is not None
        assert seconds > 60

    def test_payment_required_is_a_dead_key(self) -> None:
        exc = _status_error(402, "Payment required to access this resource.")
        assert OPENAI_STYLE.rejects_key(exc)
        assert OPENAI_STYLE.cooldown_seconds(exc) == 60 * 60
        assert OPENAI_STYLE.classify(exc) == ErrorClass.auth

    def test_structured_markers_only(self) -> None:
        # Request content echoed into a validation message must not bench
        # a healthy key for the day.
        echoed = _status_error(400, '{"error": {"message": "invalid_api_key"}}')
        assert not OPENAI_STYLE.rejects_key(echoed)
        coded = _status_error(400, '{"error": {"code": "invalid_api_key"}}')
        assert OPENAI_STYLE.rejects_key(coded)

    def test_first_line_reads_the_body(self) -> None:
        exc = _status_error(403, "The consumer_suspended project cannot be used")
        assert FIRST_LINE.rejects_key(exc)
        delay = _status_error(429, '{"error": {"details": [{"retryDelay": "42s"}]}}')
        assert FIRST_LINE.cooldown_seconds(delay) == 42

    def test_timeouts_and_outages(self) -> None:
        assert OPENAI_STYLE.cooldown_seconds(httpx.ReadTimeout("slow")) == 10
        assert OPENAI_STYLE.classify(httpx.ReadTimeout("slow")) == ErrorClass.transient
        assert OPENAI_STYLE.cooldown_seconds(_status_error(503)) == 60

    def test_unparsable_reply_is_not_benched(self) -> None:
        assert OPENAI_STYLE.cooldown_seconds(ValueError("bad json")) is None
        assert OPENAI_STYLE.classify(ValueError("bad json")) == ErrorClass.malformed


@pytest.mark.asyncio
class TestProviderFailures:
    async def test_a_failing_key_is_benched_and_the_chain_advances(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        pool = KeyPool(redis, "gemini", ["ka"], rpm=10)
        provider = GeminiProvider(pool)
        mocker.patch.object(
            provider._client,
            "post",
            mocker.AsyncMock(side_effect=_status_error(429, "burst")),
        )
        with pytest.raises(KeyBenched) as exc_info:
            await provider.generate("text", Lane.interactive, system="s")
        assert exc_info.value.error_class == ErrorClass.quota
        assert not exc_info.value.cool_provider
        assert await redis.ttl(COOLDOWN_KEY.format(provider="gemini", i=0)) > 0

    async def test_empty_reply_is_malformed(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        pool = KeyPool(redis, "groq", ["ka"], rpm=10)
        provider = OpenAICompatible("groq", url="https://x", model="m", pool=pool)
        mocker.patch.object(
            provider._client,
            "post",
            mocker.AsyncMock(return_value=_response(200, '{"choices": []}')),
        )
        with pytest.raises(KeyBenched) as exc_info:
            await provider.generate("text", Lane.interactive)
        assert exc_info.value.error_class == ErrorClass.malformed
        # Nothing about capacity: the key stays available.
        assert await pool.available()


@pytest.mark.asyncio
class TestAvailability:
    async def test_lane_availability_follows_keys_benches_and_the_paid_cap(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        _configure(mocker, GEMINI_API_KEY="g", ANTHROPIC_API_KEY="k")
        mocker.patch.object(settings, "LLM_PAID_DAILY_CAP", 25)
        chains = build_chains(redis)
        assert await chains.available(Lane.interactive)
        assert await chains.available(Lane.background)
        await redis.set(COOLDOWN_KEY.format(provider="gemini", i=0), "1")
        assert not await chains.available(Lane.background)
        assert await chains.available(Lane.interactive)
        import time

        from outception.news.summaries.providers.governor import _day

        await redis.set(CAP_PAID_DAY.format(day=_day(time.time())), "25")
        assert not await chains.available(Lane.interactive)

    async def test_kill_switch(self, redis: Redis, mocker: MockerFixture) -> None:
        _configure(mocker, GEMINI_API_KEY="g")
        mocker.patch.object(settings, "LLM_DISABLED", True)
        assert not await build_chains(redis).available(Lane.interactive)
