import sys
from typing import Any

from sentry_sdk.types import Event

from outception.exceptions import OutceptionError
from outception.news.summary import SummaryUnavailable
from outception.sentry import before_send


def _hint(exc: Exception) -> dict[str, Any]:
    try:
        raise exc
    except Exception:
        return {"exc_info": sys.exc_info()}


def test_drops_expected_errors() -> None:
    event: Event = {"tags": {}}
    assert before_send(event, _hint(SummaryUnavailable())) is None


def test_keeps_faults() -> None:
    event: Event = {"tags": {}}
    assert before_send(event, _hint(OutceptionError("boom"))) is event


def test_keeps_events_without_exception() -> None:
    event: Event = {"tags": {}}
    assert before_send(event, {}) is event


def test_drops_operational_errors() -> None:
    event: Event = {"tags": {"is_operational_error": "true"}}
    assert before_send(event, {}) is None
