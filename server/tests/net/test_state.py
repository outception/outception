import pytest

from outception.net.state import (
    FALLBACK_AFTER_SECONDS,
    FailureRecord,
    SignalState,
    clear_failure,
    derive,
    note_failure,
    read_failure,
    worst,
)
from outception.redis import Redis


def test_worst_wins() -> None:
    assert worst([]) == SignalState.nominal
    assert (
        worst([SignalState.nominal, SignalState.stale, SignalState.degraded])
        == SignalState.stale
    )
    assert (
        worst([SignalState.fallback, SignalState.unavailable])
        == SignalState.unavailable
    )


class TestDerive:
    def test_fresh(self) -> None:
        assert (
            derive(age_ms=1000, interval_ms=5000, ttl_ms=60000, failure=None)
            == SignalState.nominal
        )

    def test_stale_past_interval(self) -> None:
        assert (
            derive(age_ms=9000, interval_ms=5000, ttl_ms=60000, failure=None)
            == SignalState.stale
        )

    def test_degraded_on_failure_with_data(self) -> None:
        failure = FailureRecord(fail_since=1000.0, last_error_class="transient")
        assert (
            derive(
                age_ms=9000, interval_ms=5000, ttl_ms=60000, failure=failure, now=1100.0
            )
            == SignalState.degraded
        )

    def test_fallback_after_a_day(self) -> None:
        failure = FailureRecord(fail_since=0.0, last_error_class="transient")
        assert (
            derive(
                age_ms=9000,
                interval_ms=5000,
                ttl_ms=60000,
                failure=failure,
                now=FALLBACK_AFTER_SECONDS,
            )
            == SignalState.fallback
        )

    def test_unavailable_without_data(self) -> None:
        assert (
            derive(age_ms=None, interval_ms=5000, ttl_ms=60000, failure=None)
            == SignalState.unavailable
        )


@pytest.mark.asyncio
class TestFailureRecord:
    async def test_round_trip(self, redis: Redis) -> None:
        assert await read_failure(redis, "bbc-world") is None
        await note_failure(redis, "bbc-world", "transient")
        first = await read_failure(redis, "bbc-world")
        assert first is not None
        assert first.last_error_class == "transient"
        await note_failure(redis, "bbc-world", "quota")
        second = await read_failure(redis, "bbc-world")
        assert second is not None
        assert second.fail_since == first.fail_since
        assert second.last_error_class == "quota"
        await clear_failure(redis, "bbc-world")
        assert await read_failure(redis, "bbc-world") is None
