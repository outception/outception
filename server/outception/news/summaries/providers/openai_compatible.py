"""One class for every OpenAI-style chat endpoint: the second line of free
capacity (five vendors today) and the own generation endpoint when one is
configured. Whole-result only: the panel types out single-chunk results,
and a generation is a couple of seconds either way."""

from collections.abc import AsyncIterator

import httpx

from .base import Reply
from .classes import ErrorClass, KeyBenched, PoolExhausted
from .discipline import OPENAI_STYLE, Discipline
from .lanes import Lane
from .pool import KeyPool

# Matches the first-line ceiling for a summary, with room for longer
# replies; providers meter what the model writes, not the ceiling.
MAX_COMPLETION_TOKENS = 2000

_client = httpx.AsyncClient(timeout=30.0)


class OpenAICompatible:
    discipline: Discipline = OPENAI_STYLE

    def __init__(
        self,
        id: str,
        *,
        url: str,
        model: str,
        pool: KeyPool,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.id = id
        self.url = url
        self.model = model
        self.pool = pool
        self._client = client or _client

    async def ready(self) -> bool:
        return await self.pool.available()

    def _body(self, prompt: str, system: str | None) -> dict[str, object]:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        body: dict[str, object] = {
            "model": self.model,
            "messages": messages,
            "max_completion_tokens": MAX_COMPLETION_TOKENS,
            "stream": False,
        }
        if "gpt-oss" in self.model:
            # A reasoning model: without this it spends its token budget
            # thinking and returns truncated or empty content.
            body["reasoning_effort"] = "low"
        return body

    async def generate(
        self, prompt: str, lane: Lane, *, system: str | None = None
    ) -> Reply:
        slot = await self.pool.acquire()
        if slot is None:
            raise PoolExhausted(self.id)
        try:
            response = await self._client.post(
                self.url,
                headers={
                    "Authorization": f"Bearer {slot.key}",
                    "content-type": "application/json",
                },
                json=self._body(prompt, system),
            )
            response.raise_for_status()
            data = response.json()
            choices = data.get("choices") or []
            message = (choices[0].get("message") or {}) if choices else {}
            text = str(message.get("content") or "").strip()
            if not text:
                raise ValueError("empty reply")
            usage = data.get("usage") or {}
        except (httpx.HTTPError, ValueError) as exc:
            rejected = self.discipline.rejects_key(exc)
            await self.pool.note_failure(
                slot.index, self.discipline.cooldown_seconds(exc), rejected=rejected
            )
            raise KeyBenched(
                self.id, self.discipline.classify(exc), key_index=slot.index
            ) from exc
        return Reply(
            text=text,
            model=self.model,
            tokens_in=int(usage.get("prompt_tokens") or 0),
            tokens_out=int(usage.get("completion_tokens") or 0),
        )

    async def stream(
        self, prompt: str, lane: Lane, *, system: str | None = None
    ) -> AsyncIterator[str]:
        reply = await self.generate(prompt, lane, system=system)
        yield reply.text

    def classify(self, exc: Exception) -> ErrorClass:
        if isinstance(exc, KeyBenched | PoolExhausted):
            return exc.error_class
        return self.discipline.classify(exc)
