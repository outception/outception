"""The house decision model: a `Decider` over `POST {ENGINE_URL}/decide`,
authenticated with `X-Engine-Key`. It answers typed questions with
calibrated probabilities in one forward pass and writes no prose. When an
own generation endpoint exists it also serves as a `Provider` through the
same shape the other endpoints use; until then `generate` raises.

The request body is the same question object `llm_decider` renders into a
prompt, so the two cannot drift.
"""

import time
from collections.abc import AsyncIterator
from typing import Any

import httpx

from outception.config import settings

from .base import Answer, Decision, Question, QuestionKind, Reply
from .classes import ErrorClass, ModelError
from .lanes import Lane


def decide_body(state: dict[str, Any], questions: list[Question]) -> dict[str, Any]:
    return {
        "state": state,
        "questions": [
            {
                "id": question.id,
                "kind": question.kind.value,
                "text": question.text,
                "options": list(question.options),
                "criteria": dict(question.criteria),
            }
            for question in questions
        ],
    }


def parse_decision(
    payload: dict[str, Any], questions: list[Question]
) -> dict[str, Answer]:
    raw_answers = payload.get("answers")
    if not isinstance(raw_answers, dict):
        raise ValueError("no answers")
    answers: dict[str, Answer] = {}
    for question in questions:
        raw = raw_answers.get(question.id)
        if not isinstance(raw, dict):
            raise ValueError(f"missing answer for {question.id}")
        probabilities = raw.get("probabilities")
        if not isinstance(probabilities, dict) or not probabilities:
            raise ValueError(f"{question.id}: no probabilities")
        probabilities = {str(k): float(v) for k, v in probabilities.items()}
        chosen = str(
            raw.get("chosen") or max(probabilities, key=lambda k: probabilities[k])
        )
        if question.kind == QuestionKind.bool:
            if chosen not in {"true", "false"}:
                raise ValueError(f"{question.id}: {chosen!r} is not a bool")
        elif chosen not in question.options:
            raise ValueError(f"{question.id}: {chosen!r} is not an option")
        expected = raw.get("expected")
        answers[question.id] = Answer(
            question.kind,
            probabilities,
            chosen,
            float(expected) if expected is not None else None,
        )
    return answers


class OwnModel:
    id = "own"

    def __init__(
        self,
        *,
        url: str | None = None,
        key: str | None = None,
        timeout: float | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.url = (url or settings.ENGINE_URL or "").rstrip("/")
        self._key = key
        self.timeout = timeout if timeout is not None else settings.ENGINE_TIMEOUT_S
        self._client = client

    @property
    def configured(self) -> bool:
        return bool(self.url)

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._key:
            headers["X-Engine-Key"] = self._key
        return headers

    async def decide(
        self, state: dict[str, Any], questions: list[Question], lane: Lane
    ) -> Decision:
        if not self.configured:
            raise ModelError(
                self.id, ErrorClass.transient, detail="engine not configured"
            )
        started = time.monotonic()
        body = decide_body(state, questions)
        try:
            if self._client is not None:
                response = await self._client.post(
                    f"{self.url}/decide",
                    json=body,
                    headers=self._headers(),
                    timeout=self.timeout,
                )
            else:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.url}/decide", json=body, headers=self._headers()
                    )
        except httpx.TimeoutException as e:
            raise ModelError(self.id, ErrorClass.transient, detail="timeout") from e
        except httpx.HTTPError as e:
            raise ModelError(self.id, ErrorClass.transient, detail="unreachable") from e
        if response.status_code in (401, 403):
            raise ModelError(self.id, ErrorClass.auth)
        if response.status_code == 429 or response.status_code >= 500:
            raise ModelError(
                self.id, ErrorClass.transient, detail=str(response.status_code)
            )
        if response.status_code >= 400:
            raise ModelError(
                self.id, ErrorClass.malformed, detail=str(response.status_code)
            )
        try:
            payload = response.json()
            answers = parse_decision(payload, questions)
        except ValueError as e:
            raise ModelError(self.id, ErrorClass.malformed, detail=str(e)) from e
        model = str(payload.get("model") or "own")
        return Decision(
            answers=answers,
            model=f"own:{model}" if not model.startswith("own:") else model,
            latency_ms=int((time.monotonic() - started) * 1000),
            calibrated=bool(payload.get("calibrated", True)),
        )

    async def health(self) -> bool:
        """True when the engine answers its health route. Health reads never
        trigger work; this is one GET."""
        if not self.configured:
            return False
        try:
            if self._client is not None:
                response = await self._client.get(
                    f"{self.url}/health", timeout=self.timeout
                )
            else:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(f"{self.url}/health")
        except httpx.HTTPError:
            return False
        return response.status_code == 200

    async def ready(self) -> bool:
        return self.configured

    async def generate(
        self, prompt: str, lane: Lane, *, system: str | None = None
    ) -> Reply:
        if not settings.OWN_GENERATION_URL:
            raise ModelError(
                self.id, ErrorClass.transient, detail="no generation endpoint"
            )
        raise ModelError(self.id, ErrorClass.transient, detail="generation not wired")

    async def stream(
        self, prompt: str, lane: Lane, *, system: str | None = None
    ) -> AsyncIterator[str]:
        reply = await self.generate(prompt, lane, system=system)
        yield reply.text

    def classify(self, exc: Exception) -> ErrorClass:
        if isinstance(exc, ModelError):
            return exc.error_class
        return ErrorClass.transient
