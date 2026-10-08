"""A `Decider` rendered onto any `Provider`: the questions become the strict
JSON contract the scorer uses, the reply is parsed back into a `Decision`.
One source for the questions, two renderings (this one and the engine's
`/decide` body), so a switch between them cannot drift."""

import json
import re
import time
from typing import Any

from .base import Answer, Decision, Provider, Question, QuestionKind
from .classes import ErrorClass, ModelError
from .lanes import Lane

MAX_STATE_CHARS = 4000

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def render_prompt(state: dict[str, Any], questions: list[Question]) -> str:
    """The contract: answer every question with a JSON object keyed by
    question id; a choice names one option, a score names one level, a bool
    is true or false. Nothing else in the reply."""
    lines = [
        "Answer the questions about the item below. Reply with one JSON object",
        "and nothing else: the keys are the question ids.",
        "",
        "Item:",
        json.dumps(state, ensure_ascii=False)[:MAX_STATE_CHARS],
        "",
        "Questions:",
    ]
    for question in questions:
        if question.kind == QuestionKind.choice:
            lines.append(
                f'- "{question.id}": {question.text} One of: {", ".join(question.options)}.'
            )
        elif question.kind == QuestionKind.score:
            lines.append(
                f'- "{question.id}": {question.text} One level of: {", ".join(question.options)}.'
            )
        else:
            lines.append(f'- "{question.id}": {question.text} true or false.')
        for option, criterion in question.criteria.items():
            lines.append(f"    {option}: {criterion}")
    return "\n".join(lines)


def render_repair_prompt(original: str, reply: str) -> str:
    return (
        original
        + "\n\nYour previous reply was not one JSON object with every question id as a key:\n"
        + reply[:500]
        + "\n\nReply again with only the JSON object."
    )


def parse_reply(text: str, questions: list[Question]) -> dict[str, Answer]:
    match = _JSON_RE.search(text or "")
    if match is None:
        raise ValueError("no JSON object in reply")
    try:
        raw = json.loads(match.group(0))
    except json.JSONDecodeError as e:
        raise ValueError("reply is not JSON") from e
    if not isinstance(raw, dict):
        raise ValueError("reply is not an object")
    answers: dict[str, Answer] = {}
    for question in questions:
        if question.id not in raw:
            raise ValueError(f"missing answer for {question.id}")
        answers[question.id] = _coerce(question, raw[question.id])
    return answers


def _coerce(question: Question, value: Any) -> Answer:
    if question.kind == QuestionKind.bool:
        if isinstance(value, str):
            value = value.strip().lower() in {"true", "yes", "1"}
        chosen = "true" if bool(value) else "false"
        return Answer(
            question.kind,
            {chosen: 1.0, ("false" if chosen == "true" else "true"): 0.0},
            chosen,
        )
    chosen = str(value).strip()
    if chosen not in question.options:
        lowered = {option.lower(): option for option in question.options}
        if chosen.lower() in lowered:
            chosen = lowered[chosen.lower()]
        else:
            raise ValueError(f"{question.id}: {chosen!r} is not an option")
    probabilities = {
        option: (1.0 if option == chosen else 0.0) for option in question.options
    }
    expected = None
    if question.kind == QuestionKind.score:
        expected = float(question.options.index(chosen))
    return Answer(question.kind, probabilities, chosen, expected)


class LLMDecider:
    """Decisions through a generation provider. One repair retry on a
    malformed reply, then the `malformed` class goes to the chain."""

    id = "llm_decider"

    def __init__(self, provider: Provider) -> None:
        self.provider = provider

    async def decide(
        self, state: dict[str, Any], questions: list[Question], lane: Lane
    ) -> Decision:
        started = time.monotonic()
        prompt = render_prompt(state, questions)
        reply = await self.provider.generate(prompt, lane)
        try:
            answers = parse_reply(reply.text, questions)
        except ValueError:
            repaired = await self.provider.generate(
                render_repair_prompt(prompt, reply.text), lane
            )
            try:
                answers = parse_reply(repaired.text, questions)
            except ValueError as e:
                raise ModelError(
                    self.provider.id, ErrorClass.malformed, detail=str(e)
                ) from e
            reply = repaired
        return Decision(
            answers=answers,
            model=reply.model,
            latency_ms=int((time.monotonic() - started) * 1000),
            calibrated=False,
        )

    def classify(self, exc: Exception) -> ErrorClass:
        if isinstance(exc, ModelError):
            return exc.error_class
        return self.provider.classify(exc)
