"""The paid backup: one key, counted in tokens against the paid daily cap
by the governor. It serves readers only; the background lane never
reaches it."""

import json
from collections.abc import AsyncIterator

import httpx

from outception.config import settings

from .base import Reply
from .classes import ErrorClass, KeyBenched, PoolExhausted
from .discipline import OPENAI_STYLE, Discipline
from .gemini import raise_for_stream_status
from .lanes import Lane
from .pool import KeyPool

MESSAGES_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
MAX_TOKENS = 400

_client = httpx.AsyncClient(timeout=30.0)


class PaidProvider:
    id = "paid"
    discipline: Discipline = OPENAI_STYLE

    def __init__(self, pool: KeyPool, client: httpx.AsyncClient | None = None) -> None:
        self.pool = pool
        self._client = client or _client

    @property
    def model(self) -> str:
        return settings.SUMMARY_MODEL

    async def ready(self) -> bool:
        return await self.pool.available()

    def _headers(self, key: str) -> dict[str, str]:
        return {
            "x-api-key": key,
            "anthropic-version": API_VERSION,
            "content-type": "application/json",
        }

    def _body(
        self, prompt: str, system: str | None, *, stream: bool
    ) -> dict[str, object]:
        body: dict[str, object] = {
            "model": self.model,
            "max_tokens": MAX_TOKENS,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            body["system"] = system
        if stream:
            body["stream"] = True
        return body

    async def _fail(self, index: int, exc: BaseException) -> KeyBenched:
        await self.pool.note_failure(
            index,
            self.discipline.cooldown_seconds(exc),
            rejected=self.discipline.rejects_key(exc),
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
                MESSAGES_URL,
                headers=self._headers(slot.key),
                json=self._body(prompt, system, stream=False),
            )
            response.raise_for_status()
            data = response.json()
            text = "".join(
                str(block.get("text", "")) for block in data.get("content", [])
            ).strip()
            if not text:
                raise ValueError("empty reply")
            usage = data.get("usage") or {}
        except (httpx.HTTPError, ValueError) as exc:
            raise await self._fail(slot.index, exc) from exc
        return Reply(
            text=text,
            model=self.model,
            tokens_in=int(usage.get("input_tokens") or 0),
            tokens_out=int(usage.get("output_tokens") or 0),
        )

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
                MESSAGES_URL,
                headers=self._headers(slot.key),
                json=self._body(prompt, system, stream=True),
            ) as response:
                await raise_for_stream_status(response)
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = json.loads(line[6:])
                    if data.get("type") != "content_block_delta":
                        continue
                    chunk = str((data.get("delta") or {}).get("text", ""))
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
