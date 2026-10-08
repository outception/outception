from datetime import UTC, datetime

import pytest
from pytest_mock import MockerFixture

from outception.config import settings
from outception.net.state import FailureRecord
from outception.news import source_health
from outception.redis import Redis

DAY = 86400


class TestPropose:
    def test_only_long_runs_longest_first(self) -> None:
        now = 1_000_000.0
        failures = {
            "fresh": FailureRecord(
                fail_since=now - 2 * DAY, last_error_class="transient"
            ),
            "dead": FailureRecord(
                fail_since=now - 9 * DAY, last_error_class="transient"
            ),
            "empty": FailureRecord(fail_since=now - 7 * DAY, last_error_class="empty"),
            "fine": None,
        }
        proposals = source_health.propose(failures, {"dead": "Dead Feed"}, now=now)
        assert [(p.id, p.days) for p in proposals] == [("dead", 9), ("empty", 7)]
        assert proposals[0].name == "Dead Feed"
        row = proposals[1].as_disabled_row(datetime(2026, 10, 5, tzinfo=UTC))
        assert row == {
            "id": "empty",
            "reason": "empty from the production host",
            "since": "2026-10-05",
        }

    def test_threshold_can_be_shortened(self) -> None:
        now = 1_000_000.0
        record = FailureRecord(fail_since=now - 2 * 86400, last_error_class="http")
        assert source_health.propose({"dark": record}, {}, now=now) == []
        short = source_health.propose(
            {"dark": record}, {}, now=now, threshold_seconds=86400
        )
        assert [p.id for p in short] == ["dark"]
        assert short[0].days == 2

    def test_report_lists_rows_to_paste(self) -> None:
        proposals = [source_health.Proposal("dead", "Dead Feed", 9, "transient")]
        html = source_health.report_html(
            proposals, 100, datetime(2026, 10, 5, tzinfo=UTC)
        )
        assert "1 of 100 sources" in html
        assert '"id": "dead"' in html


@pytest.mark.asyncio
class TestSendReport:
    async def test_mails_when_there_is_something_to_say(
        self,
        redis: Redis,
        mocker: MockerFixture,
    ) -> None:
        mocker.patch.object(settings, "FEEDBACK_DIGEST_EMAIL", "founder@example.com")
        enqueue = mocker.patch("outception.news.source_health.enqueue_job")
        mocker.patch.object(
            source_health,
            "collect",
            return_value=[source_health.Proposal("dead", "Dead Feed", 9, "transient")],
        )
        assert await source_health.send_report(redis) == 1
        assert "1 source(s)" in enqueue.call_args.kwargs["subject"]

    async def test_silent_when_clean(self, redis: Redis, mocker: MockerFixture) -> None:
        mocker.patch.object(settings, "FEEDBACK_DIGEST_EMAIL", "founder@example.com")
        enqueue = mocker.patch("outception.news.source_health.enqueue_job")
        mocker.patch.object(source_health, "collect", return_value=[])
        assert await source_health.send_report(redis) == 0
        enqueue.assert_not_called()
