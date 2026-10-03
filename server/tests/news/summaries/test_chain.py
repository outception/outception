from collections.abc import AsyncIterator
from typing import Any

import pytest

from outception.config import settings
from outception.news.summaries.providers.base import (
    Decision,
    Question,
    QuestionKind,
    Reply,
)
from outception.news.summaries.providers.chain import (
    ChainExhausted,
    Chains,
    Refused,
    decision_chain,
)
from outception.news.summaries.providers.classes import ErrorClass, ModelError
from outception.news.summaries.providers.governor import Governor
from outception.news.summaries.providers.lanes import Lane
from outception.news.summaries.providers.llm_decider import (
    LLMDecider,
    parse_reply,
    render_prompt,
)
from outception.redis import Redis


class FakeProvider:
    def __init__(self, id: str, replies: list[str | Exception]) -> None:
        self.id = id
        self.replies = list(replies)
        self.calls = 0

    async def ready(self) -> bool:
        return True

    async def generate(
        self, prompt: str, lane: Lane, *, system: str | None = None
    ) -> Reply:
        self.calls += 1
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return Reply(text=reply, model=f"{self.id}-model", tokens_in=10, tokens_out=5)

    async def stream(
        self, prompt: str, lane: Lane, *, system: str | None = None
    ) -> AsyncIterator[str]:
        reply = await self.generate(prompt, lane, system=system)
        yield reply.text

    def classify(self, exc: Exception) -> ErrorClass:
        if isinstance(exc, ModelError):
            return exc.error_class
        return ErrorClass.transient


QUESTIONS = [
    Question("category", QuestionKind.choice, "Which category?", ("tech", "world")),
    Question("same", QuestionKind.bool, "Same story?"),
    Question("level", QuestionKind.score, "How important?", ("low", "mid", "high")),
]


@pytest.fixture
def keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "k")
    monkeypatch.setattr(settings, "GROQ_API_KEY", "k")


def _chains(redis: Redis, *providers: FakeProvider) -> Chains:
    governor = Governor(redis)
    by_id = {provider.id: provider for provider in providers}
    deciders = {"llm_decider": LLMDecider(providers[0])} if providers else {}
    return Chains(governor, by_id, deciders)  # type: ignore[arg-type]


@pytest.mark.asyncio
@pytest.mark.usefixtures("keys")
class TestGenerate:
    async def test_first_available_provider_answers(self, redis: Redis) -> None:
        gemini = FakeProvider("gemini", ["hello"])
        groq = FakeProvider("groq", ["never"])
        reply = await _chains(redis, gemini, groq).generate("p", Lane.interactive)
        assert reply.text == "hello"
        assert groq.calls == 0

    async def test_quota_advances_and_cools(self, redis: Redis) -> None:
        gemini = FakeProvider(
            "gemini", [ModelError("gemini", ErrorClass.quota, retry_after=100)]
        )
        groq = FakeProvider("groq", ["from groq"])
        chains = _chains(redis, gemini, groq)
        reply = await chains.generate("p", Lane.interactive)
        assert reply.text == "from groq"
        assert await chains.governor.cooldown_remaining("gemini") > 0
        assert await chains.governor.used(Lane.interactive) == (1, 1)

    async def test_malformed_retries_once_then_advances(self, redis: Redis) -> None:
        gemini = FakeProvider(
            "gemini",
            [
                ModelError("gemini", ErrorClass.malformed),
                ModelError("gemini", ErrorClass.malformed),
            ],
        )
        groq = FakeProvider("groq", ["ok"])
        reply = await _chains(redis, gemini, groq).generate("p", Lane.interactive)
        assert reply.text == "ok"
        assert gemini.calls == 2

    async def test_refusal_stops(self, redis: Redis) -> None:
        gemini = FakeProvider("gemini", [ModelError("gemini", ErrorClass.refusal)])
        groq = FakeProvider("groq", ["never"])
        with pytest.raises(Refused):
            await _chains(redis, gemini, groq).generate("p", Lane.interactive)
        assert groq.calls == 0

    async def test_auth_disables_entry(self, redis: Redis) -> None:
        gemini = FakeProvider("gemini", [ModelError("gemini", ErrorClass.auth)])
        groq = FakeProvider("groq", ["ok"])
        chains = _chains(redis, gemini, groq)
        await chains.generate("p", Lane.interactive)
        assert await chains.governor.is_disabled("gemini") is True

    async def test_exhausted(self, redis: Redis) -> None:
        gemini = FakeProvider("gemini", [ModelError("gemini", ErrorClass.transient)])
        with pytest.raises(ChainExhausted):
            await _chains(redis, gemini).generate("p", Lane.interactive)


class TestRendering:
    def test_prompt_and_parse(self) -> None:
        prompt = render_prompt({"title": "x"}, QUESTIONS)
        assert '"category"' in prompt
        assert "tech, world" in prompt
        answers = parse_reply(
            'Sure: {"category": "Tech", "same": "yes", "level": "mid"}', QUESTIONS
        )
        assert answers["category"].chosen == "tech"
        assert answers["same"].chosen == "true"
        assert answers["level"].expected == 1.0

    def test_parse_rejects_missing_or_unknown(self) -> None:
        with pytest.raises(ValueError, match="missing answer"):
            parse_reply('{"category": "tech"}', QUESTIONS)
        with pytest.raises(ValueError, match="not an option"):
            parse_reply(
                '{"category": "sports", "same": true, "level": "mid"}', QUESTIONS
            )


@pytest.mark.asyncio
@pytest.mark.usefixtures("keys")
class TestDecide:
    async def test_llm_decider_repairs_once(self, redis: Redis) -> None:
        gemini = FakeProvider(
            "gemini",
            ["not json", '{"category": "tech", "same": false, "level": "high"}'],
        )
        chains = _chains(redis, gemini)
        decision = await chains.decide("category", {"title": "x"}, QUESTIONS)
        assert decision.answers["category"].chosen == "tech"
        assert decision.calibrated is False
        assert gemini.calls == 2

    async def test_shadow_never_changes_the_answer(
        self, redis: Redis, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(settings, "ENGINE_URL", "http://engine")
        monkeypatch.setattr(settings, "DECISION_SHADOW", True)
        gemini = FakeProvider(
            "gemini", ['{"category": "tech", "same": false, "level": "high"}']
        )
        chains = _chains(redis, gemini)

        class FakeOwn:
            id = "own"

            async def decide(
                self, state: dict[str, Any], questions: list[Question], lane: Lane
            ) -> Decision:
                raise ModelError("own", ErrorClass.transient)

            def classify(self, exc: Exception) -> ErrorClass:
                return ErrorClass.transient

        chains.deciders["own"] = FakeOwn()
        recorded: list[tuple[Decision | None, Decision | Exception | None]] = []

        async def shadow(
            primary: Decision | None, house: Decision | Exception | None
        ) -> None:
            recorded.append((primary, house))

        decision = await chains.decide(
            "category", {"title": "x"}, QUESTIONS, shadow=shadow
        )
        assert decision.answers["category"].chosen == "tech"
        assert len(recorded) == 1
        assert isinstance(recorded[0][1], ModelError)


def test_decision_chain_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ENGINE_URL", None)
    monkeypatch.setattr(settings, "DECISION_CHAIN_RESOLVE", "own, llm_decider")
    assert decision_chain("resolve") == ("llm_decider",)
    monkeypatch.setattr(settings, "ENGINE_URL", "http://engine")
    assert decision_chain("resolve") == ("own", "llm_decider")
    monkeypatch.setattr(settings, "DECISION_CHAIN_SCORE", "own")
    assert decision_chain("score") == ("own", "llm_decider")
