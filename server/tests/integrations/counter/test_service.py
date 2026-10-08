from datetime import date
from unittest.mock import AsyncMock

import httpx
import pytest
from pytest_mock import MockerFixture

from outception.config import settings
from outception.integrations.counter import client, service
from outception.integrations.counter.exceptions import (
    CounterError,
    CounterNotConfigured,
)


def _reply(status: int, body: object) -> httpx.Response:
    return httpx.Response(
        status, json=body, request=httpx.Request("POST", "https://counter.test/q")
    )


@pytest.fixture
def configured(mocker: MockerFixture) -> None:
    mocker.patch.object(settings, "POSTHOG_API_KEY", "phx_test")
    mocker.patch.object(settings, "POSTHOG_PROJECT_ID", "123")
    mocker.patch.object(settings, "POSTHOG_HOST", "https://counter.test")


def test_hogql_names_the_window_and_the_field() -> None:
    text = service.hogql("country", 7)
    assert "$geoip_country_code" in text
    assert "interval 7 day" in text
    # UTC days from midnight, the top keys from a subquery, newest rows first
    # so a cap only ever trims the oldest days.
    assert "toTimeZone(timestamp, 'UTC')" in text
    assert "toStartOfDay(toTimeZone(now(), 'UTC'))" in text
    assert f"limit {service.TOP_KEYS}" in text
    assert "order by day desc, views desc limit 5000" in text


def test_parse_skips_empty_keys_and_bad_rows() -> None:
    rows = service.parse(
        "path",
        [
            ["2026-10-07", "/", 12],
            ["2026-10-07", None, 3],
            ["2026-10-07", "/launches", "x"],
            ["2026-10-06T00:00:00Z", "/story/abc", "4"],
            ["bad"],
        ],
    )
    assert [(r.day, r.key, r.views) for r in rows] == [
        (date(2026, 10, 7), "/", 12),
        (date(2026, 10, 6), "/story/abc", 4),
    ]
    assert {r.dimension for r in rows} == {"path"}


def test_parse_sums_keys_that_meet_after_the_cut() -> None:
    long = "/" + "a" * 250
    rows = service.parse(
        "path",
        [
            ["2026-10-01", long + "x", 3],
            ["2026-10-01", long + "y", 4],
            ["2026-10-02", long + "x", 1],
        ],
    )
    assert sorted((r.day.isoformat(), len(r.key), r.views) for r in rows) == [
        ("2026-10-01", 200, 7),
        ("2026-10-02", 200, 1),
    ]


@pytest.mark.asyncio
class TestQuery:
    async def test_unconfigured_raises(self, mocker: MockerFixture) -> None:
        mocker.patch.object(settings, "POSTHOG_API_KEY", None)
        with pytest.raises(CounterNotConfigured):
            await client.query("select 1", name="t")

    @pytest.mark.usefixtures("configured")
    async def test_sends_the_query_with_the_bearer(self, mocker: MockerFixture) -> None:
        post = mocker.patch.object(
            client._client,
            "post",
            AsyncMock(return_value=_reply(200, {"results": [["2026-10-07", "/", 2]]})),
        )
        rows = await client.query("select 1", name="t")
        assert rows == [["2026-10-07", "/", 2]]
        call = post.call_args
        assert call.args[0] == "https://counter.test/api/projects/123/query/"
        assert call.kwargs["headers"]["Authorization"] == "Bearer phx_test"
        assert call.kwargs["json"]["query"] == {
            "kind": "HogQLQuery",
            "query": "select 1",
        }

    @pytest.mark.usefixtures("configured")
    async def test_errors_become_counter_errors(self, mocker: MockerFixture) -> None:
        mocker.patch.object(
            client._client, "post", AsyncMock(return_value=_reply(500, {"error": "x"}))
        )
        with pytest.raises(CounterError):
            await client.query("select 1", name="t")
        mocker.patch.object(
            client._client, "post", AsyncMock(return_value=_reply(200, {"nope": 1}))
        )
        with pytest.raises(CounterError):
            await client.query("select 1", name="t")

    @pytest.mark.usefixtures("configured")
    async def test_fetch_visits_parses_one_dimension(
        self, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(
            client._client,
            "post",
            AsyncMock(return_value=_reply(200, {"results": [["2026-10-07", "IE", 4]]})),
        )
        rows = await service.fetch_visits("country", 3)
        assert [(r.dimension, r.key, r.views) for r in rows] == [("country", "IE", 4)]
