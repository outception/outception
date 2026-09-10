import json
from unittest.mock import AsyncMock

import httpx
import pytest
from httpx import AsyncClient
from pytest_mock import MockerFixture

from outception.config import settings
from outception.news import free_llm, translate
from outception.redis import Redis


def _reply(*translations: str) -> str:
    return json.dumps(list(translations))


@pytest.fixture(autouse=True)
def _providers(mocker: MockerFixture) -> None:
    mocker.patch.object(settings, "GEMINI_API_KEY", "g")
    mocker.patch.object(settings, "ANTHROPIC_API_KEY", "k")


class TestParse:
    def test_plain_array(self) -> None:
        assert translate._parse('["Hallo", "Welt"]', 2) == ["Hallo", "Welt"]

    def test_strips_code_fence(self) -> None:
        assert translate._parse('```json\n["Hallo"]\n```', 1) == ["Hallo"]

    def test_tolerates_preamble_and_rejects_empty(self) -> None:
        assert translate._parse('Here you go: ["Hallo"] ', 1) == ["Hallo"]
        with pytest.raises(ValueError, match="no numbered list"):
            translate._parse("", 1)

    def test_shape_mismatch_raises(self) -> None:
        with pytest.raises(ValueError, match="shape mismatch"):
            translate._parse('["Hallo"]', 2)
        with pytest.raises(ValueError, match="no numbered list"):
            translate._parse('{"a": 1}', 1)

    def test_empty_or_non_string_items_are_misses(self) -> None:
        assert translate._parse('["", 5, "ok"]', 3) == [None, None, "ok"]


class TestChunks:
    def test_bounds_count_and_chars(self) -> None:
        many = [f"headline {i}" for i in range(100)]
        sizes = [len(c) for c in translate._chunks(many)]
        assert sum(sizes) == 100
        assert all(s <= translate._MAX_BATCH for s in sizes)
        long = ["x" * 3000, "y" * 3000]
        assert [len(c) for c in translate._chunks(long)] == [1, 1]


@pytest.mark.asyncio
class TestTranslateTexts:
    async def test_translates_batches_and_caches(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        generate = mocker.patch.object(
            translate, "_generate", AsyncMock(return_value=_reply("Hallo", "Welt"))
        )
        assert await translate.translate_texts(redis, ["Hello", "World"], "de") == [
            "Hallo",
            "Welt",
        ]
        generate.assert_awaited_once()
        system, user = generate.await_args_list[0].args[1:3]
        assert "German" in system
        assert "1. Hello" in user
        assert "2. World" in user
        # Second call is served from the cache - no model call.
        assert await translate.translate_texts(redis, ["Hello", "World"], "de") == [
            "Hallo",
            "Welt",
        ]
        generate.assert_awaited_once()

    async def test_failure_returns_original_and_is_not_cached(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        generate = mocker.patch.object(
            translate,
            "_generate",
            AsyncMock(side_effect=httpx.ConnectError("down")),
        )
        assert await translate.translate_texts(redis, ["Hello"], "de") == ["Hello"]
        assert await redis.keys("news:xlate:de:*") == []
        generate.side_effect = None
        generate.return_value = _reply("Hallo")
        assert await translate.translate_texts(redis, ["Hello"], "de") == ["Hallo"]

    async def test_shape_mismatch_is_a_failure(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(
            translate, "_generate", AsyncMock(return_value=_reply("only one"))
        )
        assert await translate.translate_texts(redis, ["a", "b"], "de") == ["a", "b"]
        assert await redis.keys("news:xlate:de:*") == []

    async def test_nonblocking_fast_batch_lands_in_soft_wait(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        generate = mocker.patch.object(
            translate, "_generate", AsyncMock(return_value=_reply("Bonjour"))
        )
        first = await translate.translate_texts(redis, ["Hello"], "fr", block=False)
        assert first == ["Bonjour"]  # a fast batch lands inside the soft wait
        generate.assert_awaited_once()

    async def test_nonblocking_slow_batch_serves_originals_then_caches(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        import asyncio

        mocker.patch.object(translate, "_SOFT_WAIT_SECONDS", 0.05)

        async def slow(*args: object, **kwargs: object) -> str:
            await asyncio.sleep(0.2)
            return _reply("Bonjour")

        generate = mocker.patch.object(
            translate, "_generate", AsyncMock(side_effect=slow)
        )
        first = await translate.translate_texts(redis, ["Hello"], "fr", block=False)
        assert first == ["Hello"]  # slow provider: originals, no hung card
        await asyncio.gather(*translate._background_tasks)
        second = await translate.translate_texts(redis, ["Hello"], "fr", block=False)
        assert second == ["Bonjour"]  # cache filled for the next poll
        generate.assert_awaited_once()

    async def test_nonblocking_pending_marker_stops_duplicates(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        import asyncio

        mocker.patch.object(translate, "_SOFT_WAIT_SECONDS", 0.05)

        async def slow(*args: object, **kwargs: object) -> str:
            await asyncio.sleep(0.2)
            return _reply("Bonjour")

        generate = mocker.patch.object(
            translate, "_generate", AsyncMock(side_effect=slow)
        )
        await translate.translate_texts(redis, ["Hello"], "fr", block=False)
        await translate.translate_texts(redis, ["Hello"], "fr", block=False)
        await asyncio.gather(*translate._background_tasks)
        generate.assert_awaited_once()

    async def test_nonblocking_reports_pending_and_waits_on_peer(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        import asyncio

        mocker.patch.object(translate, "_SOFT_WAIT_SECONDS", 0.05)

        async def slow(*args: object, **kwargs: object) -> str:
            await asyncio.sleep(0.2)
            return _reply("Bonjour")

        mocker.patch.object(translate, "_generate", AsyncMock(side_effect=slow))
        texts, pending = await translate.translate_texts_with_status(
            redis, ["Hello"], "fr", block=False
        )
        assert (texts, pending) == (["Hello"], True)
        await asyncio.gather(*translate._background_tasks)
        assert await redis.keys("news:xlate:pending:*") == []
        texts, pending = await translate.translate_texts_with_status(
            redis, ["Hello"], "fr", block=False
        )
        assert (texts, pending) == (["Bonjour"], False)

    async def test_nonblocking_failure_clears_pending_marker(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        import asyncio

        mocker.patch.object(translate, "_SOFT_WAIT_SECONDS", 0.05)
        mocker.patch.object(
            translate, "_generate", AsyncMock(side_effect=ValueError("boom"))
        )
        _, pending = await translate.translate_texts_with_status(
            redis, ["Hello"], "fr", block=False
        )
        assert pending is True
        await asyncio.gather(*translate._background_tasks, return_exceptions=True)
        assert await redis.keys("news:xlate:pending:*") == []

    async def test_nonblocking_starved_batch_is_parked_briefly(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        import asyncio

        mocker.patch.object(translate, "_SOFT_WAIT_SECONDS", 0.05)
        mocker.patch.object(
            translate,
            "_generate",
            AsyncMock(
                side_effect=translate.NoTranslationCapacity(
                    "paid translation cap reached"
                )
            ),
        )
        texts = ["Hello", "World"]
        _, pending = await translate.translate_texts_with_status(
            redis, texts, "fr", block=False
        )
        assert pending is True
        await asyncio.gather(*translate._background_tasks, return_exceptions=True)
        ttl = await redis.ttl(translate._failed_key("fr", texts))
        assert 0 < ttl <= translate._STARVED_TTL_SECONDS

    async def test_ascii_english_skips_the_model(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        generate = mocker.patch.object(translate, "_generate", AsyncMock())
        out = await translate.translate_texts(redis, ["Plain English headline"], "en")
        assert out == ["Plain English headline"]
        generate.assert_not_awaited()
        assert await redis.keys("news:xlate:v3:en:*") == []

    async def test_typographic_english_skips_the_model(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        generate = mocker.patch.object(translate, "_generate", AsyncMock())
        text = "Trump\u2019s \u201cbig\u201d plan \u2014 explained\u2026"
        assert await translate.translate_texts(redis, [text], "en") == [text]
        generate.assert_not_awaited()
        assert translate._needs_model("\u00dcber alles", "en")

    async def test_paid_cap_brakes_anthropic_only(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "TRANSLATION_PAID_DAILY_CAP", 1)
        mocker.patch.object(settings, "GEMINI_API_KEY", None)
        anthropic = mocker.patch.object(
            translate, "_generate_anthropic", AsyncMock(return_value=_reply("Hallo"))
        )
        assert await translate.translate_texts(redis, ["Hello"], "de") == ["Hallo"]
        # Second paid call is over the cap: original returned, nothing cached.
        assert await translate.translate_texts(redis, ["World"], "de") == ["World"]
        anthropic.assert_awaited_once()
        assert await redis.get(translate._cache_key("de", "World")) is None

    async def test_warmer_spends_its_own_small_budget(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "TRANSLATION_WARMER_PAID_DAILY_CAP", 1)
        mocker.patch.object(
            translate,
            "_generate_gemini",
            AsyncMock(side_effect=httpx.ReadTimeout("stalled")),
        )
        anthropic = mocker.patch.object(
            translate, "_generate_anthropic", AsyncMock(return_value=_reply("Hallo"))
        )
        first = await translate.translate_texts(redis, ["Hello"], "de", budget="warmer")
        assert first == ["Hallo"]
        # Warmer over ITS cap: stops, while the reader budget stays untouched.
        second = await translate.translate_texts(
            redis, ["World"], "de", budget="warmer"
        )
        assert second == ["World"]
        anthropic.assert_awaited_once()
        reader = await translate.translate_texts(redis, ["Again"], "de")
        assert reader == ["Hallo"]  # reader budget still live

    async def test_warmer_free_tier_cap(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "TRANSLATION_WARMER_FREE_DAILY_CAP", 1)
        gemini = mocker.patch.object(
            translate, "_generate_gemini", AsyncMock(return_value=_reply("Hallo"))
        )
        anthropic = mocker.patch.object(
            translate, "_generate_anthropic", AsyncMock(return_value=_reply("Welt"))
        )
        assert await translate.translate_texts(
            redis, ["Hello"], "de", budget="warmer"
        ) == ["Hallo"]
        # Over its free share the warmer leaves the rest of the day's free
        # quota to live readers and continues on its own paid allowance.
        assert await translate.translate_texts(
            redis, ["World"], "de", budget="warmer"
        ) == ["Welt"]
        gemini.assert_awaited_once()
        anthropic.assert_awaited_once()
        # Readers are unaffected by the warmer's share.
        assert await translate.translate_texts(redis, ["Again"], "de") == ["Hallo"]

    async def test_free_llm_serves_before_paid(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        """Provider order with the second free line configured: Gemini fails,
        Groq picks the batch up, and the paid backup is never called."""
        mocker.patch.object(settings, "GROQ_API_KEY", "gsk_test")
        mocker.patch.object(
            translate,
            "_generate_gemini",
            AsyncMock(side_effect=httpx.ReadTimeout("stalled")),
        )
        free = mocker.patch.object(
            free_llm, "generate", AsyncMock(return_value=_reply("Hallo"))
        )
        anthropic = mocker.patch.object(translate, "_generate_anthropic", AsyncMock())

        assert await translate.translate_texts(redis, ["Hello"], "de") == ["Hallo"]
        free.assert_awaited_once()
        anthropic.assert_not_awaited()

    async def test_free_llm_failure_falls_through_to_paid(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "GROQ_API_KEY", "gsk_test")
        mocker.patch.object(settings, "GEMINI_API_KEY", None)
        mocker.patch.object(
            free_llm,
            "generate",
            AsyncMock(side_effect=httpx.ReadTimeout("stalled")),
        )
        anthropic = mocker.patch.object(
            translate, "_generate_anthropic", AsyncMock(return_value=_reply("Hallo"))
        )

        assert await translate.translate_texts(redis, ["Hello"], "de") == ["Hallo"]
        anthropic.assert_awaited_once()
        # …and the failing endpoint is benched for the next batch.
        assert not await free_llm.available(redis)

    async def test_gemini_is_not_counted_against_the_paid_cap(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "TRANSLATION_PAID_DAILY_CAP", 0)
        gemini = mocker.patch.object(
            translate, "_generate_gemini", AsyncMock(return_value=_reply("Hallo"))
        )
        assert await translate.translate_texts(redis, ["Hello"], "de") == ["Hallo"]
        gemini.assert_awaited_once()

    async def test_demand_is_noted_for_supported_non_english_targets(
        self, redis: Redis
    ) -> None:
        await translate.note_demand(redis, "de")
        await translate.note_demand(redis, "en")
        await translate.note_demand(redis, "xx")
        assert await translate.demanded_targets(redis) == ["de"]

    async def test_demand_ranks_by_recent_readers(self, redis: Redis) -> None:
        for _ in range(3):
            await translate.note_demand(redis, "hr")
        await translate.note_demand(redis, "de")
        assert await translate.demanded_targets(redis) == ["hr", "de"]

    async def test_source_language_demand_needs_repeat_readers(
        self, redis: Redis
    ) -> None:
        """One hit never qualifies (a caller cycling ?lang= must not buy
        translations); English and junk targets are ignored; the list is
        ranked and capped."""
        for target, hits in (("hr", 2), ("de", 5), ("sl", 1), ("fr", 3), ("it", 2)):
            for _ in range(hits):
                await translate.note_source_language_demand(redis, "src", target)
        await translate.note_source_language_demand(redis, "src", "en")
        await translate.note_source_language_demand(redis, "src", "xx")
        assert await translate.source_demanded_targets(redis, "src") == [
            "de",
            "fr",
            "hr",
        ]
        assert await translate.source_demanded_targets(redis, "other") == []

    async def test_translate_ahead_covers_demanded_languages_except_skip(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        for target in ("hr", "de"):
            for _ in range(2):
                await translate.note_source_language_demand(redis, "src", target)
        texts_mock = mocker.patch.object(
            translate, "translate_texts", AsyncMock(return_value=["x"])
        )
        translate.spawn_translate_ahead(redis, "src", ["Hello"], skip="de")
        await translate.drain_translate_ahead(timeout=5)
        # The warmer's budget: background warming must not compete with live
        # readers for the per-minute slots that are the real bottleneck.
        texts_mock.assert_awaited_once_with(redis, ["Hello"], "hr", budget="warmer")

    async def test_translate_ahead_swallows_provider_failures(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        for _ in range(2):
            await translate.note_source_language_demand(redis, "src", "hr")
        mocker.patch.object(
            translate,
            "translate_texts",
            AsyncMock(side_effect=translate.NoTranslationCapacity("spent")),
        )
        await translate.translate_ahead(redis, "src", ["Hello"])

    async def test_unsupported_target_and_unconfigured_are_passthrough(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        generate = mocker.patch.object(translate, "_generate", AsyncMock())
        assert await translate.translate_texts(redis, ["Hello"], "xx") == ["Hello"]
        mocker.patch.object(settings, "GEMINI_API_KEY", None)
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", None)
        assert await translate.translate_texts(redis, ["Hello"], "de") == ["Hello"]
        generate.assert_not_awaited()
        assert await redis.keys("news:xlate:*") == []

    async def test_many_headlines_split_into_chunks(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        async def echo(_redis: Redis, _system: str, user: str, _budget: str) -> str:
            lines = []
            for line in user.splitlines():
                num, _, text = line.partition(". ")
                lines.append(f"{num}. {text}!")
            return "\n".join(lines)

        generate = mocker.patch.object(
            translate, "_generate", AsyncMock(side_effect=echo)
        )
        texts = [f"headline {i}" for i in range(100)]
        out = await translate.translate_texts(redis, texts, "fr")
        assert out == [f"{t}!" for t in texts]
        assert generate.await_count == -(-100 // translate._MAX_BATCH)


@pytest.mark.asyncio
class TestProviders:
    async def test_gemini_first(self, redis: Redis, mocker: MockerFixture) -> None:
        gemini = mocker.patch.object(
            translate, "_generate_gemini", AsyncMock(return_value="[]")
        )
        anthropic = mocker.patch.object(translate, "_generate_anthropic", AsyncMock())
        assert await translate._generate(redis, "s", "u", "reader") == "[]"
        gemini.assert_awaited_once()
        anthropic.assert_not_awaited()

    async def test_falls_back_to_anthropic(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(
            translate,
            "_generate_gemini",
            AsyncMock(side_effect=httpx.ConnectError("down")),
        )
        anthropic = mocker.patch.object(
            translate, "_generate_anthropic", AsyncMock(return_value='["x"]')
        )
        assert await translate._generate(redis, "s", "u", "reader") == '["x"]'
        anthropic.assert_awaited_once()

    async def test_gemini_failure_starts_cooldown(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        gemini = mocker.patch.object(
            translate,
            "_generate_gemini",
            AsyncMock(side_effect=httpx.ReadTimeout("stalled")),
        )
        mocker.patch.object(
            translate, "_generate_anthropic", AsyncMock(return_value='["x"]')
        )
        await translate._generate(redis, "s", "u", "reader")
        await translate._generate(redis, "s", "u", "reader")
        gemini.assert_awaited_once()  # skipped while the cooldown key is set

    async def test_a_dead_key_falls_over_to_the_next_gemini_key(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        """A key dying mid-call used to take the whole batch off Gemini with
        it, even with healthy keys left in the pool, pushing the batch onto
        slower free lanes and then onto the paid card. It must try a
        neighbour first."""
        mocker.patch.object(settings, "GEMINI_API_KEYS", "a,b,c")
        used: list[str] = []

        async def _flaky(system: str, user: str, key: str) -> str:
            used.append(key)
            if len(used) == 1:
                raise httpx.ReadTimeout("quota spent")
            return _reply("Hallo")

        mocker.patch.object(translate, "_generate_gemini", _flaky)
        anthropic = mocker.patch.object(
            translate, "_generate_anthropic", AsyncMock(return_value=_reply("x"))
        )

        await translate._generate(redis, "s", "u", "reader")

        assert len(used) == 2, "gave up on Gemini after one dead key"
        assert used[0] != used[1], "retried the same key instead of the next"
        anthropic.assert_not_awaited()  # never reached the paid card

    async def test_gemini_failure_without_backup_raises(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", None)
        mocker.patch.object(
            translate,
            "_generate_gemini",
            AsyncMock(side_effect=httpx.ConnectError("down")),
        )
        with pytest.raises(translate.NoTranslationCapacity):
            await translate._generate(redis, "s", "u", "reader")

    async def test_reader_asks_the_fastest_free_provider_first(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        """Groq has been answering in 600 ms, Gemini in 2.5 s: a reader's
        batch goes to Groq and Gemini is not touched."""
        mocker.patch.object(settings, "GROQ_API_KEY", "gsk_test")
        await translate._note_latency(redis, "gemini", 2500)
        await translate._note_latency(redis, "groq", 600)
        assert await translate.reader_provider_order(redis) == ["groq", "gemini"]
        gemini = mocker.patch.object(translate, "_generate_gemini", AsyncMock())
        free = mocker.patch.object(free_llm, "generate", AsyncMock(return_value="[]"))
        assert await translate._generate(redis, "s", "u", "reader") == "[]"
        free.assert_awaited_once()
        gemini.assert_not_awaited()

    async def test_latency_is_learned_from_real_calls(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "GROQ_API_KEY", "gsk_test")
        mocker.patch.object(translate, "_generate_gemini", AsyncMock(return_value="[]"))
        assert await translate.reader_provider_order(redis) == ["gemini", "groq"]
        await translate._generate(redis, "s", "u", "reader")
        assert await redis.get(translate._LATENCY_KEY.format(provider="gemini"))

    async def test_nvidia_is_the_warmers_first_free_llm_line(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        """With Gemini's warmer share spent, a warmer batch goes to NVIDIA's
        slow-but-strong lane rather than to Groq, whose quota readers need;
        a reader with Groq and NVIDIA both healthy still gets Groq."""
        mocker.patch.object(settings, "GROQ_API_KEY", "gsk_test")
        mocker.patch.object(settings, "NVIDIA_API_KEY", "nvapi_test")
        mocker.patch.object(settings, "TRANSLATION_WARMER_FREE_DAILY_CAP", 0)
        seen: list[str] = []

        async def generate(_system: str, _user: str, endpoint: object) -> str:
            seen.append(getattr(endpoint, "provider"))
            return "[]"

        mocker.patch.object(free_llm, "generate", AsyncMock(side_effect=generate))
        mocker.patch.object(free_llm, "_ROUND_ROBIN_KEY", "test:rr")
        await redis.set("test:rr", "0")
        for _ in range(4):
            await translate._generate(redis, "s", "u", "warmer")
        assert set(seen) <= {"nvidia", "groq"}
        assert "nvidia" in seen
        seen.clear()
        await translate._note_latency(redis, "groq", 600)
        await translate._note_latency(redis, "nvidia", 6000)
        mocker.patch.object(translate, "_generate_gemini", AsyncMock(return_value=""))
        await translate._generate(redis, "s", "u", "reader")
        assert seen == ["groq"]

    async def test_fast_pool_spills_to_the_next_provider_when_minute_full(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        """Parallel chunks of one card spread out: once the fastest provider
        has used its minute, the next chunk goes to the next one."""
        mocker.patch.object(settings, "GROQ_API_KEY", "gsk_test")
        mocker.patch.object(settings, "GROQ_RPM_CAP", 1)
        await translate._note_latency(redis, "groq", 500)
        await translate._note_latency(redis, "gemini", 2000)
        gemini = mocker.patch.object(
            translate, "_generate_gemini", AsyncMock(return_value="[]")
        )
        free = mocker.patch.object(free_llm, "generate", AsyncMock(return_value="[]"))
        await translate._generate(redis, "s", "u", "reader")
        await translate._generate(redis, "s", "u", "reader")
        free.assert_awaited_once()
        gemini.assert_awaited_once()

    async def test_mistral_is_a_last_resort_for_readers(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "GROQ_API_KEY", "gsk_test")
        mocker.patch.object(settings, "MISTRAL_API_KEY", "m_test")
        mocker.patch.object(settings, "GEMINI_API_KEY", None)
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", None)
        seen: list[str] = []

        async def generate(_system: str, _user: str, endpoint: object) -> str:
            provider = getattr(endpoint, "provider")
            seen.append(provider)
            if provider == "groq":
                raise httpx.ReadTimeout("stalled")
            return "[]"

        mocker.patch.object(free_llm, "generate", AsyncMock(side_effect=generate))
        assert await translate._generate(redis, "s", "u", "reader") == "[]"
        assert seen == ["groq", "mistral"]

    async def test_warmer_never_uses_the_last_resort_line(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        """Mistral's per-minute allowance is for readers: an out-of-quota
        warmer must go paid (its own small budget) or stand down."""
        mocker.patch.object(settings, "MISTRAL_API_KEY", "m_test")
        mocker.patch.object(settings, "GEMINI_API_KEY", None)
        free = mocker.patch.object(free_llm, "generate", AsyncMock(return_value="[]"))
        anthropic = mocker.patch.object(
            translate, "_generate_anthropic", AsyncMock(return_value="[]")
        )
        await translate._generate(redis, "s", "u", "warmer")
        free.assert_not_awaited()
        anthropic.assert_awaited_once()
        # And with the paid allowance gone too, it reports itself broke even
        # though Mistral is up.
        mocker.patch.object(settings, "TRANSLATION_WARMER_FREE_DAILY_CAP", 0)
        mocker.patch.object(settings, "TRANSLATION_WARMER_PAID_DAILY_CAP", 0)
        assert await translate.warmer_out_of_budget(redis) is True

    async def test_warmer_keeps_gemini_first_whatever_the_latency(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "GROQ_API_KEY", "gsk_test")
        await translate._note_latency(redis, "groq", 300)
        await translate._note_latency(redis, "gemini", 3000)
        gemini = mocker.patch.object(
            translate, "_generate_gemini", AsyncMock(return_value="[]")
        )
        free = mocker.patch.object(free_llm, "generate", AsyncMock())
        await translate._generate(redis, "s", "u", "warmer")
        gemini.assert_awaited_once()
        free.assert_not_awaited()

    async def test_nvidia_never_serves_a_reader(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        """Background-only: with every quick lane out, a reader goes to the
        last-resort line, never to NVIDIA's unpredictable queue."""
        mocker.patch.object(settings, "GEMINI_API_KEY", None)
        mocker.patch.object(settings, "NVIDIA_API_KEY", "nvapi_test")
        mocker.patch.object(settings, "MISTRAL_API_KEY", "m_test")
        seen: list[str] = []

        async def generate(_system: str, _user: str, endpoint: object) -> str:
            seen.append(getattr(endpoint, "provider"))
            return "[]"

        mocker.patch.object(free_llm, "generate", AsyncMock(side_effect=generate))
        assert await translate._generate(redis, "s", "u", "reader") == "[]"
        assert seen == ["mistral"]

    async def test_reader_hedges_a_slow_lane_with_the_next(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        """Gemini is the quickest on record but stalls this time: after the
        hedge delay Groq is started too, its reply wins, and the stalled
        Gemini attempt is cancelled rather than awaited."""
        import asyncio

        mocker.patch.object(settings, "GROQ_API_KEY", "gsk_test")
        mocker.patch.object(translate, "_HEDGE_AFTER_SECONDS", 0.05)
        cancelled = asyncio.Event()

        async def stalled(*_args: object, **_kwargs: object) -> str:
            try:
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                cancelled.set()
                raise
            return '["late"]'

        mocker.patch.object(
            translate, "_generate_gemini", AsyncMock(side_effect=stalled)
        )
        free = mocker.patch.object(
            free_llm, "generate", AsyncMock(return_value='["quick"]')
        )
        started = asyncio.get_running_loop().time()
        assert await translate._generate(redis, "s", "u", "reader") == '["quick"]'
        assert asyncio.get_running_loop().time() - started < 2
        free.assert_awaited_once()
        await asyncio.wait_for(cancelled.wait(), 1)

    async def test_reader_moves_on_at_once_when_a_lane_is_empty(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        """An unavailable lane (benched, minute-full) must not cost the hedge
        delay: the next lane starts immediately."""
        import asyncio

        mocker.patch.object(settings, "GROQ_API_KEY", "gsk_test")
        mocker.patch.object(settings, "GEMINI_API_KEY", None)
        mocker.patch.object(translate, "_HEDGE_AFTER_SECONDS", 5.0)
        mocker.patch.object(settings, "GROQ_RPM_CAP", 0)  # groq minute-full
        mocker.patch.object(settings, "MISTRAL_API_KEY", "m_test")
        free = mocker.patch.object(free_llm, "generate", AsyncMock(return_value="[]"))
        started = asyncio.get_running_loop().time()
        assert await translate._generate(redis, "s", "u", "reader") == "[]"
        assert asyncio.get_running_loop().time() - started < 1
        assert free.await_args_list[0].args[2].provider == "mistral"


@pytest.mark.asyncio
class TestTranslateEndpoint:
    async def test_english_target_is_a_noop(
        self, client: AsyncClient, mocker: MockerFixture
    ) -> None:
        generate = mocker.patch.object(translate, "_generate", AsyncMock())
        response = await client.post(
            "/v1/news/translate", json={"texts": ["Hello"], "target": "en"}
        )
        assert response.status_code == 200
        assert response.json()["translations"] == ["Hello"]
        generate.assert_not_awaited()

    async def test_serves_cache_hits_and_returns_misses_unchanged(
        self, client: AsyncClient, redis: Redis, mocker: MockerFixture
    ) -> None:
        # Cache-only by design: the route takes caller-supplied text, and
        # translating that cached the model's reply under the real headline's
        # hash - a poisoning and budget-drain lever. Misses come back as-is
        # and the model is never called.
        generate = mocker.patch.object(translate, "_generate", AsyncMock())
        await redis.set(translate._cache_key("de", "Hello"), "Hallo")
        response = await client.post(
            "/v1/news/translate", json={"texts": ["Hello", "World"], "target": "de"}
        )
        assert response.status_code == 200
        assert response.json()["translations"] == ["Hallo", "World"]
        generate.assert_not_awaited()

    async def test_empty_texts_rejected(self, client: AsyncClient) -> None:
        response = await client.post(
            "/v1/news/translate", json={"texts": [], "target": "de"}
        )
        assert response.status_code == 422


@pytest.mark.asyncio
class TestGeminiDiscipline:
    def _status_error(self, status: int, body: str) -> httpx.HTTPStatusError:
        request = httpx.Request("POST", "https://generativelanguage.googleapis.com/x")
        response = httpx.Response(status, text=body, request=request)
        return httpx.HTTPStatusError("boom", request=request, response=response)

    async def test_per_minute_429_is_a_short_cooldown(self) -> None:
        from outception.news import gemini

        exc = self._status_error(429, '{"error": {"details": [{"retryDelay": "17s"}]}}')
        assert gemini.cooldown_seconds(exc) == 17

    async def test_daily_quota_429_benches_gemini_for_long(self) -> None:
        from outception.news import gemini

        exc = self._status_error(
            429, '{"error": {"message": "Quota exceeded for GenerateRequestsPerDay"}}'
        )
        seconds = gemini.cooldown_seconds(exc)
        assert seconds is not None
        assert seconds >= 30 * 60

    async def test_empty_reply_is_not_a_cooldown(self) -> None:
        from outception.news import gemini

        assert gemini.cooldown_seconds(ValueError("empty translation")) is None

    async def test_timeout_is_a_short_cooldown(self) -> None:
        from outception.news import gemini

        timeout = gemini.cooldown_seconds(httpx.ReadTimeout(""))
        outage = gemini.cooldown_seconds(httpx.ConnectError(""))
        assert timeout is not None
        assert outage is not None
        assert timeout < outage

    async def test_reader_goes_paid_when_the_minute_is_spent(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "GEMINI_RPM_CAP", 1)
        gemini_mock = mocker.patch.object(
            translate, "_generate_gemini", AsyncMock(return_value=_reply("Hallo"))
        )
        anthropic = mocker.patch.object(
            translate, "_generate_anthropic", AsyncMock(return_value=_reply("Hallo"))
        )
        assert await translate.translate_texts(redis, ["Hello"], "de") == ["Hallo"]
        assert await translate.translate_texts(redis, ["World"], "de") == ["Hallo"]
        gemini_mock.assert_awaited_once()
        anthropic.assert_awaited_once()

    async def test_paid_failure_is_not_charged(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "GEMINI_API_KEY", None)
        mocker.patch("outception.news.translate.asyncio.sleep", AsyncMock())
        mocker.patch.object(
            translate,
            "_generate_anthropic",
            AsyncMock(side_effect=httpx.ConnectError("down")),
        )
        assert await translate.translate_texts(redis, ["Hello"], "de") == ["Hello"]
        assert await redis.keys("news:xlate:paid:*") == []


class TestNumberedReplies:
    def test_numbered_lines_with_quotes(self) -> None:
        raw = "1. Trump: 'Ich bin rückständig und arm'\n2. Duffy dankt Zeldin für das Ende der 'Start-Stopp'-Funktion\n"
        assert translate._parse(raw, 2) == [
            "Trump: 'Ich bin rückständig und arm'",
            "Duffy dankt Zeldin für das Ende der 'Start-Stopp'-Funktion",
        ]

    def test_numbered_lines_tolerate_fence_and_paren(self) -> None:
        raw = "```\n1) Erste\n2) Zweite\n```"
        assert translate._parse(raw, 2) == ["Erste", "Zweite"]

    def test_json_array_still_accepted(self) -> None:
        assert translate._parse('["Eins", "Zwei"]', 2) == ["Eins", "Zwei"]

    def test_incomplete_list_fails(self) -> None:
        with pytest.raises(ValueError, match="no numbered list"):
            translate._parse("1. Nur eine", 2)

    def test_numbered_payload(self) -> None:
        assert translate._numbered(["A 'quoted' one", "B"]) == "1. A 'quoted' one\n2. B"


@pytest.mark.asyncio
class TestGeminiKeyPool:
    def _daily_429(self) -> httpx.HTTPStatusError:
        request = httpx.Request("POST", "https://generativelanguage.googleapis.com/x")
        response = httpx.Response(
            429,
            text='{"error":{"message":"Quota exceeded for GenerateRequestsPerDay"}}',
            request=request,
        )
        return httpx.HTTPStatusError("boom", request=request, response=response)

    async def test_failover_to_next_key(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        from outception.news import gemini

        mocker.patch.object(settings, "GEMINI_API_KEY", None)
        mocker.patch.object(settings, "GEMINI_API_KEYS", "keyA,keyB,keyC")
        # Round-robin pool: a benched key never comes back until its cooldown
        # clears; the pool keeps serving from the survivors.
        first = await gemini.acquire(redis, 100)
        assert first is not None
        await gemini.note_failure(redis, first[0], self._daily_429())
        second = await gemini.acquire(redis, 100)
        assert second is not None
        assert second[0] != first[0]
        await gemini.note_failure(redis, second[0], self._daily_429())
        third = await gemini.acquire(redis, 100)
        assert third is not None
        assert third[0] not in {first[0], second[0]}
        assert await gemini.available(redis) is True
        # All benched -> nothing, availability False (translate then goes paid).
        await gemini.note_failure(redis, third[0], self._daily_429())
        assert await gemini.acquire(redis, 100) is None
        assert await gemini.available(redis) is False

    async def test_reader_uses_the_live_key(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        from outception.news import gemini

        mocker.patch.object(settings, "GEMINI_API_KEY", None)
        mocker.patch.object(settings, "GEMINI_API_KEYS", "keyA,keyB")
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", "k")
        seen: list[str] = []

        async def gen(system: str, user: str, key: str) -> str:
            seen.append(key)
            return _reply("Hallo")

        mocker.patch.object(translate, "_generate_gemini", gen)
        await gemini.note_failure(redis, 0, self._daily_429())  # keyA spent
        assert await translate._generate(redis, "s", "u", "reader") == _reply("Hallo")
        assert seen == ["keyB"]


class TestSerbianCyrillic:
    """Serbian is digraphic and the model answers in Latin about half the
    time, which put two alphabets on one card (measured 15 of 30 live)."""

    def test_latin_becomes_cyrillic(self) -> None:
        assert (
            translate.to_serbian_cyrillic("Pronađene bebe orangutana u indijskoj šumi")
            == "Пронађене бебе орангутана у индијској шуми"
        )

    def test_digraphs_become_one_letter(self) -> None:
        # nj/lj/dž are single Cyrillic letters, so they must be replaced
        # before the letter-by-letter pass turns them into two.
        assert translate.to_serbian_cyrillic("Njegov ljubimac džem") == (
            "Његов љубимац џем"
        )
        assert translate.to_serbian_cyrillic("NJEGOV LJUBIMAC DŽEM") == (
            "ЊЕГОВ ЉУБИМАЦ ЏЕМ"
        )

    def test_cyrillic_and_empty_are_untouched(self) -> None:
        already = "Шпанска обавештајна служба упозорила"
        assert translate.to_serbian_cyrillic(already) == already
        assert translate.to_serbian_cyrillic("") == ""

    @pytest.mark.asyncio
    async def test_chunk_converts_before_validating(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        """A Latin reply must reach the cache as Cyrillic, not be rejected -
        rejecting it would leave the reader with English."""
        mocker.patch.object(
            translate,
            "_generate",
            AsyncMock(return_value=_reply("Preminuo prvi lider Hongkonga")),
        )
        out = await translate.translate_texts(
            redis, ["Hong Kong's first leader dies"], "sr"
        )
        assert out == ["Преминуо први лидер Хонгконга"]

    @pytest.mark.asyncio
    async def test_other_cyrillic_languages_are_not_converted(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        """ru/uk/bg measured 30 of 30 in Cyrillic: they must pass through
        untouched, so a Latin word inside them still fails validation."""
        mocker.patch.object(
            translate, "_generate", AsyncMock(return_value=_reply("Hongkong lider"))
        )
        assert await translate.translate_texts(redis, ["Hong Kong leader"], "ru") == [
            "Hongkong lider"
        ]


class TestEchoedSource:
    def test_identical_long_sentence_is_miss(self) -> None:
        t = "The Scientist Trying to Keep Kratom Legal Has Ties to Lobbyists"
        assert translate._echoed_source(t, t, "hr") is True

    def test_short_identical_title_passes(self) -> None:
        assert translate._echoed_source("Tesla Model 3", "Tesla Model 3", "hr") is False

    def test_translated_text_passes(self) -> None:
        assert (
            translate._echoed_source(
                "Znanstvenik koji pokušava zadržati kratom legalnim",
                "The Scientist Trying to Keep Kratom Legal",
                "hr",
            )
            is False
        )

    def test_english_target_passes(self) -> None:
        t = "Congress averts a government shutdown ahead of the midterms"
        assert translate._echoed_source(t, t, "en") is False

    def test_echoed_headline_without_word_spaces_is_a_miss(self) -> None:
        """Japanese, Chinese and Thai write no spaces between words, so the
        word count is 1 for a whole headline and every echo used to slip
        through - a Japanese headline was cached as the Croatian translation
        for the full 7-day TTL with the card reporting itself done."""
        for headline in (
            "日本政府は新たな経済対策を発表した",
            "中国政府は新しい経済政策を発表しました",
            "รัฐบาลไทยประกาศมาตรการเศรษฐกิจใหม่",
        ):
            assert translate._echoed_source(headline, headline, "hr") is True

    def test_short_spaceless_title_still_passes(self) -> None:
        """A brand or proper noun in the same scripts can legitimately echo."""
        for title in ("任天堂", "ソニー", "ไทย"):
            assert translate._echoed_source(title, title, "hr") is False


@pytest.mark.asyncio
class TestParkedBatchesStayPending:
    async def test_parked_misses_report_pending(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "GEMINI_API_KEYS", "k")
        texts = ["Congress averts a government shutdown ahead of the midterms"]
        await redis.set(translate._failed_key("fr", texts), "1", ex=600)
        results, pending = await translate.translate_texts_with_status(
            redis, texts, "fr", block=False
        )
        assert results == texts
        assert pending is True


class TestFusedScript:
    def test_summaries_reject_fused_chars_even_when_page_carries_them(self) -> None:
        # The Croatian card that shipped "Irska ima jasne政策 okvire": the
        # scraped page carried the characters in footer junk, which excused
        # the model fusing them mid-word. Summaries validate strictly.
        summary = "Irska ima jasne政策 okvire za energetsku tranziciju."
        source = "Article text with footer junk 政策 somewhere in it."
        assert (
            translate.script_mismatch(summary, "hr", source, strict_fused=True) is True
        )

    def test_translations_keep_fused_brand_names_from_the_headline(self) -> None:
        # "小米SU7" fuses scripts legitimately; a translation preserving the
        # source headline's characters must not be rejected.
        item = "Xiaomi 小米SU7 stiže u Europu"
        source = "Xiaomi 小米SU7 arrives in Europe"
        assert translate.script_mismatch(item, "hr", source) is False

    def test_translations_reject_fused_chars_the_headline_never_had(self) -> None:
        item = "Irska ima jasne政策 okvire"
        source = "Ireland has clear policy frameworks"
        assert translate.script_mismatch(item, "hr", source) is True

    def test_quoted_foreign_name_with_boundaries_still_passes(self) -> None:
        summary = "ByteDance (字节跳动) objavio je nove rezultate."
        source = "ByteDance (字节跳动) posted new results today."
        assert translate.script_mismatch(summary, "hr", source) is False


@pytest.mark.asyncio
class TestWarmerBudget:
    async def test_out_of_budget_only_when_both_pools_spent(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        from datetime import UTC, datetime

        mocker.patch.object(settings, "TRANSLATION_WARMER_FREE_DAILY_CAP", 10)
        mocker.patch.object(settings, "TRANSLATION_WARMER_PAID_DAILY_CAP", 5)
        day = datetime.now(UTC).strftime("%Y%m%d")
        assert await translate.warmer_out_of_budget(redis) is False
        await redis.set(translate._WARMER_FREE_DAILY_KEY.format(day=day), "11")
        assert await translate.warmer_out_of_budget(redis) is False
        await redis.set(translate._PAID_DAILY_KEY.format(budget="warmer", day=day), "5")
        assert await translate.warmer_out_of_budget(redis) is True


@pytest.mark.asyncio
class TestSerbianEchoValidation:
    """The Serbian card converts Latin replies to Cyrillic. That conversion
    used to run BEFORE the echo check, which rewrote an echoed English
    headline letter-by-letter into Cyrillic; it then matched neither the
    source nor a script check and was cached as Serbian for seven days."""

    async def test_echoed_english_is_not_transliterated_into_gibberish(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        source = "Trump says he will meet Putin in Hungary next week"
        # The model echoes the source both times (first pass and echo retry).
        mocker.patch.object(
            translate, "_generate_parsed", AsyncMock(return_value=[source])
        )
        values = await translate._translate_chunk(redis, [source], "sr", "reader")
        # Accepted as "the model insisting", so it caches the ORIGINAL - never
        # the transliterated "Трумп саyс хе wилл меет" gibberish.
        assert values == [source]

    async def test_latin_serbian_reply_is_converted(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        source = "Babies of orangutans found in an Indian forest"
        latin = "Pronađene bebe orangutana u indijskoj šumi"
        mocker.patch.object(
            translate, "_generate_parsed", AsyncMock(return_value=[latin])
        )
        (value,) = await translate._translate_chunk(redis, [source], "sr", "reader")
        assert value == translate.to_serbian_cyrillic(latin)
        assert value != latin

    async def test_echo_retry_result_is_converted_too(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        """The retry path skipped the conversion, so a correct Latin-Serbian
        retry cached in Latin beside its Cyrillic neighbours."""
        source = "Babies of orangutans found in an Indian forest"
        latin = "Pronađene bebe orangutana u indijskoj šumi"
        mocker.patch.object(
            translate,
            "_generate_parsed",
            AsyncMock(side_effect=[[source], [latin]]),  # echo, then a real one
        )
        (value,) = await translate._translate_chunk(redis, [source], "sr", "reader")
        assert value == translate.to_serbian_cyrillic(latin)


class TestMixedCyrillicWord:
    """`to_serbian_cyrillic` leaves an already-Cyrillic reply untouched and
    defers a mixed one "for the script validator to reject" - but
    `script_mismatch` allows Latin everywhere, so nothing rejected it and a
    half-Latin word cached for the 7-day TTL."""

    def test_latin_fused_into_a_cyrillic_word_is_rejected(self) -> None:
        for bad in (
            "Технika за манипулацију сателитским фотографијама",
            "25 година након 11. септембра, Трамp персонификује нацију",
        ):
            assert translate._mixed_cyrillic_word(bad, "sr") is True
            assert translate._mixed_cyrillic_word(bad, "ru") is True

    def test_standalone_brand_names_are_allowed(self) -> None:
        for ok in (
            "Waymo ефекат: како вештачка интелигенција тихо мења истраживање",
            "RTK извештава о уштеди токена",
            "Нови iPhone-ов модел стиже у септембру",
        ):
            assert translate._mixed_cyrillic_word(ok, "sr") is False

    def test_latin_script_targets_are_untouched(self) -> None:
        # Croatian is Latin-script: this check must not apply there at all.
        assert translate._mixed_cyrillic_word("Технika za manipulaciju", "hr") is False
