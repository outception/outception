"""Chains: the ordered providers a call walks, lane-aware, advancing on the
error class. Generation chains serve summaries; decision chains serve the
scorer, router, matcher and resolver, with `llm_decider` always last so a
house-model outage degrades to today's behaviour, never to nulls.

The chain owns the governor calls: reserve before a provider is tried,
settle after, cool down or disable on the class the provider reports.
"""

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Any

from outception.config import settings

from .base import Decider, Decision, Provider, Question, Reply, Task
from .classes import ErrorClass, ModelError
from .cost import estimate_units, real_units
from .governor import PAID_PROVIDERS, CapExceeded, Governor, LaneDisabled
from .lanes import Consumer, Lane

LLM_DECIDER = "llm_decider"
HEDGE_AFTER_SECONDS = 2.5

# Every chain's second entry is a different provider family, so one vendor
# outage never empties a chain. The paid provider serves readers only.
GENERATION_CHAINS: dict[Lane, tuple[str, ...]] = {
    Lane.interactive: ("gemini", "groq", "ollama", "cloudflare", "mistral", "paid"),
    Lane.background: ("gemini", "nvidia", "ollama", "cloudflare", "groq"),
}

TYPICAL_REPLY_TOKENS: dict[Lane, int] = {Lane.interactive: 300, Lane.background: 120}


def generation_chain(lane: Lane) -> tuple[str, ...]:
    """The lane's provider order; the own generation endpoint goes first
    when one is configured."""
    entries = GENERATION_CHAINS[lane]
    if settings.OWN_GENERATION_URL:
        return ("own", *entries)
    return entries


def decision_chain(task: Task) -> tuple[str, ...]:
    """The per-task provider order from config; `llm_decider` is appended
    when missing and `own` is dropped when the engine is not configured."""
    raw = {
        "score": settings.DECISION_CHAIN_SCORE,
        "category": settings.DECISION_CHAIN_CATEGORY,
        "route": settings.DECISION_CHAIN_ROUTE,
        "resolve": settings.DECISION_CHAIN_RESOLVE,
    }[task]
    entries = [entry.strip() for entry in raw.split(",") if entry.strip()]
    if not settings.ENGINE_URL:
        entries = [entry for entry in entries if entry != "own"]
    if LLM_DECIDER not in entries:
        entries.append(LLM_DECIDER)
    return tuple(entries)


class ChainExhausted(ModelError):
    def __init__(self, lane: Lane) -> None:
        super().__init__("chain", ErrorClass.quota, detail=f"{lane} lane exhausted")
        self.lane = lane


class Refused(ModelError):
    """The model declined. Callers return a safe null."""

    def __init__(self, provider: str) -> None:
        super().__init__(provider, ErrorClass.refusal)


@dataclass
class Chains:
    governor: Governor
    providers: dict[str, Provider]
    deciders: dict[str, Decider]

    async def _advance_on(
        self,
        provider_id: str,
        error: Exception,
        classify: Callable[[Exception], ErrorClass],
    ) -> ErrorClass:
        error_class = classify(error)
        if isinstance(error, ModelError) and not error.cool_provider:
            # The provider's pool benched the one key that failed and may
            # still hold others: advance for this call, nothing more.
            return error_class
        retry_after = getattr(error, "retry_after", None)
        if error_class in (ErrorClass.quota, ErrorClass.transient):
            await self.governor.cool_down(provider_id, retry_after)
        elif error_class == ErrorClass.auth:
            await self.governor.disable(provider_id)
        return error_class

    async def _usable(self, provider_id: str, provider: Provider) -> bool:
        if not await self.governor.available(provider_id):
            return False
        if provider_id in PAID_PROVIDERS and (
            await self.governor.paid_used() >= settings.LLM_PAID_DAILY_CAP
        ):
            return False
        ready = getattr(provider, "ready", None)
        if ready is None:
            return True
        return bool(await ready())

    async def available(self, lane: Lane, chain: Sequence[str] | None = None) -> bool:
        """Whether some provider of the lane could serve right now: not
        killed, configured, not disabled or cooling down, with an unbenched
        key, and under the paid cap. A prognosis; reserves nothing."""
        if settings.LLM_DISABLED:
            return False
        for provider_id in chain or generation_chain(lane):
            provider = self.providers.get(provider_id)
            if provider is not None and await self._usable(provider_id, provider):
                return True
        return False

    async def generate(
        self,
        prompt: str,
        lane: Lane,
        *,
        system: str | None = None,
        consumer: Consumer | None = None,
        chain: Sequence[str] | None = None,
    ) -> Reply:
        """Walk the lane's chain. `quota` and `transient` advance; `malformed`
        retries once on the same provider, then advances; `refusal` stops
        with `Refused`; `auth` disables the entry and advances."""
        entries = list(chain or generation_chain(lane))
        if settings.LLM_DISABLED:
            raise LaneDisabled("chain")
        for provider_id in entries:
            provider = self.providers.get(provider_id)
            if provider is None or not await self._usable(provider_id, provider):
                continue
            units = estimate_units(
                provider=provider_id,
                prompt_chars=len(prompt) + len(system or ""),
                typical_reply_tokens=TYPICAL_REPLY_TOKENS[lane],
            )
            try:
                reservation = await self.governor.reserve(
                    lane, provider_id, units, consumer=consumer
                )
            except CapExceeded as error:
                if error.which in ("lane or global", f"{consumer} sub"):
                    raise ChainExhausted(lane) from error
                continue
            attempts = 0
            while True:
                attempts += 1
                try:
                    reply = await provider.generate(prompt, lane, system=system)
                except Exception as error:
                    error_class = await self._advance_on(
                        provider_id, error, provider.classify
                    )
                    if error_class == ErrorClass.malformed and attempts < 2:
                        continue
                    await self.governor.settle(reservation, 0)
                    if error_class == ErrorClass.refusal:
                        raise Refused(provider_id) from error
                    break
                await self.governor.settle(
                    reservation,
                    real_units(
                        provider=provider_id,
                        tokens_in=reply.tokens_in,
                        tokens_out=reply.tokens_out,
                    ),
                )
                return reply
        raise ChainExhausted(lane)

    async def stream(
        self,
        prompt: str,
        lane: Lane,
        *,
        system: str | None = None,
        consumer: Consumer | None = None,
        chain: Sequence[str] | None = None,
    ) -> AsyncIterator[str]:
        """The streaming twin of `generate`: the same order, reservations
        and advancing, yielding text as the model writes it. A provider that
        fails before producing anything is advanced past; one that fails
        mid-stream raises, because text is already on the reader's screen.
        The reservation is refreshed while the stream runs and settled on
        the estimate when it ends."""
        entries = list(chain or generation_chain(lane))
        if settings.LLM_DISABLED:
            raise LaneDisabled("chain")
        for provider_id in entries:
            provider = self.providers.get(provider_id)
            if provider is None or not await self._usable(provider_id, provider):
                continue
            units = estimate_units(
                provider=provider_id,
                prompt_chars=len(prompt) + len(system or ""),
                typical_reply_tokens=TYPICAL_REPLY_TOKENS[lane],
            )
            try:
                reservation = await self.governor.reserve(
                    lane, provider_id, units, consumer=consumer
                )
            except CapExceeded as error:
                if error.which in ("lane or global", f"{consumer} sub"):
                    raise ChainExhausted(lane) from error
                continue
            produced = False
            try:
                async for chunk in provider.stream(prompt, lane, system=system):
                    produced = True
                    yield chunk
            except Exception as error:
                if produced:
                    await self.governor.settle(reservation, units)
                    raise
                error_class = await self._advance_on(
                    provider_id, error, provider.classify
                )
                await self.governor.settle(reservation, 0)
                if error_class == ErrorClass.refusal:
                    raise Refused(provider_id) from error
                continue
            await self.governor.settle(reservation, units)
            return
        raise ChainExhausted(lane)

    async def decide(
        self,
        task: Task,
        state: dict[str, Any],
        questions: list[Question],
        *,
        lane: Lane = Lane.background,
        consumer: Consumer | None = None,
        shadow: Callable[
            [Decision | None, Decision | Exception | None], Awaitable[None]
        ]
        | None = None,
    ) -> Decision:
        """Walk the task's decision chain. With `DECISION_SHADOW` on and the
        house model configured but not primary, the house model is asked in
        parallel; its answer is recorded through `shadow` and never used,
        and a slow engine is cancelled at its timeout."""
        entries = decision_chain(task)
        shadow_task: asyncio.Task[Decision] | None = None
        own = self.deciders.get("own")
        if (
            settings.DECISION_SHADOW
            and own is not None
            and entries[0] != "own"
            and settings.ENGINE_URL
        ):
            shadow_task = asyncio.create_task(own.decide(state, questions, lane))
        decision: Decision | None = None
        failure: Exception | None = None
        try:
            for decider_id in entries:
                decider = self.deciders.get(decider_id)
                if decider is None:
                    continue
                if decider_id != LLM_DECIDER and not await self.governor.available(
                    decider_id
                ):
                    continue
                try:
                    reservation = await self.governor.reserve(
                        lane, decider_id, 1, consumer=consumer
                    )
                except CapExceeded as error:
                    failure = error
                    continue
                try:
                    decision = await decider.decide(state, questions, lane)
                except Exception as error:
                    await self._advance_on(decider_id, error, decider.classify)
                    await self.governor.settle(reservation, 0)
                    failure = error
                    continue
                await self.governor.settle(reservation, 1)
                break
        finally:
            if shadow_task is not None and shadow is not None:
                shadow_result: Decision | Exception | None
                try:
                    shadow_result = await asyncio.wait_for(
                        shadow_task, settings.ENGINE_TIMEOUT_S
                    )
                except Exception as error:
                    shadow_result = error
                await shadow(decision, shadow_result)
            elif shadow_task is not None:
                shadow_task.cancel()
        if decision is None:
            if isinstance(failure, ModelError):
                raise failure
            raise ChainExhausted(lane)
        return decision
