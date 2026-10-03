"""The two protocols every model call goes through, and the shared value
objects. A `Provider` writes prose; a `Decider` answers typed questions
with calibrated probabilities and writes none."""

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Literal, Protocol

from .classes import ErrorClass
from .lanes import Lane


@dataclass(frozen=True)
class Reply:
    text: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0


class QuestionKind(StrEnum):
    choice = "choice"
    score = "score"
    bool = "bool"


@dataclass(frozen=True)
class Question:
    """One typed question. `options` names the choices for `choice`, the
    ordered levels for `score`; `bool` has none."""

    id: str
    kind: QuestionKind
    text: str
    options: tuple[str, ...] = ()
    criteria: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Answer:
    kind: QuestionKind
    probabilities: dict[str, float]
    chosen: str
    expected: float | None = None  # for score questions: the probability-weighted level


@dataclass(frozen=True)
class Decision:
    answers: dict[str, Answer]
    model: str
    latency_ms: int
    calibrated: bool


Task = Literal["score", "category", "route", "resolve"]


class Provider(Protocol):
    id: str

    async def generate(self, prompt: str, lane: Lane) -> Reply: ...

    def stream(self, prompt: str, lane: Lane) -> AsyncIterator[str]: ...

    def classify(self, exc: Exception) -> ErrorClass: ...


class Decider(Protocol):
    id: str

    async def decide(
        self, state: dict[str, Any], questions: list[Question], lane: Lane
    ) -> Decision: ...

    def classify(self, exc: Exception) -> ErrorClass: ...
