"""The first-line free provider: a key pool over the generative language
endpoint, with and without streaming."""

import json
from collections.abc import AsyncIterator

import httpx

from outception.config import settings

from .base import Reply
from .classes import ErrorClass, KeyBenched, PoolExhausted
from .discipline import FIRST_LINE, Discipline
from .lanes import Lane
from .pool import KeyPool

GENERATE_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)
STREAM_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}"
    ":streamGenerateContent?alt=sse"
)
MAX_OUTPUT_TOKENS = 400

_client = httpx.AsyncClient(timeout=30.0)


async def raise_for_stream_status(response: httpx.Response) -> None:
    """raise_for_status for a streaming response: the error body has to be
    read first, or the client raises ResponseNotRead instead of the HTTP
    error."""
    if response.status_code >= 400:
        await response.aread()
        response.raise_for_status()


def _parts_text(data: dict[str, object]) -> str:
    candidates = data.get("candidates") or []
    if not isinstance(candidates, list) or not candidates:
        return ""
    content = candidates[0].get("content") or {}
    parts = content.get("parts", []) if isinstance(content, dict) else []
    return "".join(str(part.get("text", "")) for part in parts)


class GeminiProvider:
    id = "gemini"
    discipline: Discipline = FIRST_LINE

    def __init__(self, pool: KeyPool, client: httpx.AsyncClient | None = None) -> None:
        self.pool = pool
        self._client = client or _client

    @property
    def model(self) -> str:
        return settings.GEMINI_SUMMARY_MODEL

    async def ready(self) -> bool:
        return await self.pool.available()

    def _body(self, prompt: str, system: str | None) -> dict[str, object]:
        body: dict[str, object] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": MAX_OUTPUT_TOKENS},
        }
        if system:
            body["system_instruction"] = {"parts": [{"text": system}]}
        return body

    async def _fail(self, index: int, exc: BaseException) -> KeyBenched:
        rejected = self.discipline.rejects_key(exc)
        await self.pool.note_failure(
            index, self.discipline.cooldown_seconds(exc), rejected=rejected
        )
        return KeyBenched(self.id, self.discipline.classify(exc), key_index=index)

    async def generate(
        self, prompt: str, lane: Lane, *, system: str | None = None
    ) -> Reply:
        slot = await self.pool.acquire()
        if slot is None:
            raise PoolExhausted(self.id)
        try:
            response = await self._client.post(
                GENERATE_URL.format(model=self.model),
                headers={
                    "x-goog-api-key": slot.key,
                    "content-type": "application/json",
                },
                json=self._body(prompt, system),
            )
            response.raise_for_status()
            text = _parts_text(response.json()).strip()
            if not text:
                raise ValueError("empty reply")
        except (httpx.HTTPError, ValueError) as exc:
            raise await self._fail(slot.index, exc) from exc
        return Reply(text=text, model=self.model)

    async def stream(
        self, prompt: str, lane: Lane, *, system: str | None = None
    ) -> AsyncIterator[str]:
        slot = await self.pool.acquire()
        if slot is None:
            raise PoolExhausted(self.id)
        produced = False
        try:
            async with self._client.stream(
                "POST",
                STREAM_URL.format(model=self.model),
                headers={
                    "x-goog-api-key": slot.key,
                    "content-type": "application/json",
                },
                json=self._body(prompt, system),
            ) as response:
                await raise_for_stream_status(response)
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    chunk = _parts_text(json.loads(line[6:]))
                    if chunk:
                        produced = True
                        yield chunk
            if not produced:
                raise ValueError("empty reply")
        except (httpx.HTTPError, httpx.StreamError, ValueError) as exc:
            if produced:
                raise
            raise await self._fail(slot.index, exc) from exc

    def classify(self, exc: Exception) -> ErrorClass:
        if isinstance(exc, KeyBenched | PoolExhausted):
            return exc.error_class
        return self.discipline.classify(exc)
