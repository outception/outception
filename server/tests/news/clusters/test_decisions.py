import pytest

from outception.news.clusters import decisions
from outception.news.summaries.providers.base import Answer, Decision, QuestionKind
from outception.redis import Redis


def _decision(score: str, sure: float = 1.0) -> Decision:
    rest = (1 - sure) / 2
    levels = {"6": rest, "7": rest, "8": rest}
    levels[score] = sure
    return Decision(
        answers={"score": Answer(QuestionKind.score, levels, score)},
        model="x",
        latency_ms=10,
        calibrated=True,
    )


class TestBrier:
    def test_sure_and_right_is_zero_sure_and_wrong_is_two(self) -> None:
        assert decisions.brier(_decision("7"), _decision("7")) == 0.0
        assert decisions.brier(_decision("7"), _decision("8")) == 2.0
        # Shadow says 8 at 0.5, 6 and 7 at 0.25 each; the rendered choice is 7.
        assert decisions.brier(
            _decision("7"), _decision("8", sure=0.5)
        ) == pytest.approx(0.0625 + 0.5625 + 0.25)
        assert decisions.brier(_decision("7"), Decision({}, "x", 1, True)) is None


@pytest.mark.asyncio
class TestReport:
    async def test_counts_agreement_errors_latency_and_brier(
        self, redis: Redis
    ) -> None:
        record = decisions.record_shadow(redis, "score")
        await record(_decision("7"), _decision("7"))
        await record(_decision("7"), _decision("8", sure=0.5))
        await record(_decision("7"), RuntimeError("down"))
        report = await decisions.shadow_report(redis, "score")
        assert report["total"] == 3
        assert report["agreement"] == 0.5
        assert report["error_rate"] == pytest.approx(0.333)
        assert report["mean_latency_ms"] == 10
        assert report["brier"] == pytest.approx((0 + 0.875) / 2, abs=0.001)
