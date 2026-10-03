import httpx
import pytest

from outception.news.summaries.providers.base import Question, QuestionKind
from outception.news.summaries.providers.classes import ErrorClass, ModelError
from outception.news.summaries.providers.lanes import Lane
from outception.news.summaries.providers.own import OwnModel, decide_body

QUESTIONS = [
    Question("same", QuestionKind.bool, "Same story?"),
    Question("category", QuestionKind.choice, "Which?", ("tech", "world")),
]


def _client(handler: httpx.MockTransport) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=handler)


@pytest.mark.asyncio
async def test_decide_posts_the_question_object_and_parses() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["key"] = request.headers.get("X-Engine-Key")
        seen["body"] = request.read()
        return httpx.Response(
            200,
            json={
                "model": "ckpt-3",
                "calibrated": True,
                "answers": {
                    "same": {
                        "probabilities": {"true": 0.9, "false": 0.1},
                        "chosen": "true",
                    },
                    "category": {"probabilities": {"tech": 0.7, "world": 0.3}},
                },
            },
        )

    own = OwnModel(
        url="http://engine", key="secret", client=_client(httpx.MockTransport(handler))
    )
    decision = await own.decide({"title": "x"}, QUESTIONS, Lane.background)
    assert seen["path"] == "/decide"
    assert seen["key"] == "secret"
    assert b'"questions"' in seen["body"]  # type: ignore[operator]
    assert decision.model == "own:ckpt-3"
    assert decision.calibrated is True
    assert decision.answers["category"].chosen == "tech"
    assert decision.answers["same"].probabilities["true"] == 0.9


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "error_class"),
    [
        (401, ErrorClass.auth),
        (503, ErrorClass.transient),
        (429, ErrorClass.transient),
        (422, ErrorClass.malformed),
    ],
)
async def test_status_to_error_class(status: int, error_class: ErrorClass) -> None:
    own = OwnModel(
        url="http://engine",
        client=_client(httpx.MockTransport(lambda r: httpx.Response(status))),
    )
    with pytest.raises(ModelError) as excinfo:
        await own.decide({}, QUESTIONS, Lane.background)
    assert excinfo.value.error_class == error_class


@pytest.mark.asyncio
async def test_unreachable_is_transient() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    own = OwnModel(url="http://engine", client=_client(httpx.MockTransport(handler)))
    with pytest.raises(ModelError) as excinfo:
        await own.decide({}, QUESTIONS, Lane.background)
    assert excinfo.value.error_class == ErrorClass.transient
    assert await own.health() is False


def test_body_mirrors_the_question_object() -> None:
    body = decide_body({"title": "x"}, QUESTIONS)
    assert body["questions"][1] == {
        "id": "category",
        "kind": "choice",
        "text": "Which?",
        "options": ["tech", "world"],
        "criteria": {},
    }
