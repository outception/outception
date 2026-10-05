"""Shadow-mode bookkeeping for the decision chains: every call where the
house model answered in parallel counts as one comparison, agreement is
when every chosen answer matches, calibration is the Brier score of the
shadow's probabilities against the rendered choice (0 is perfect, lower
is better), and a capped sample is kept for the report."""

import json
from collections.abc import Awaitable, Callable
from typing import Any

from outception.redis import Redis

from ..summaries.providers.base import Decision

TOTAL_KEY = "news:decisions:shadow:{task}:total"
AGREE_KEY = "news:decisions:shadow:{task}:agree"
ERROR_KEY = "news:decisions:shadow:{task}:errors"
LATENCY_KEY = "news:decisions:shadow:{task}:latency_ms"
# The Brier sum in thousandths, so Redis can add integers.
BRIER_KEY = "news:decisions:shadow:{task}:brier_milli"
SAMPLE_KEY = "news:decisions:shadow:{task}:sample"
SAMPLE_MAX = 200
TTL_SECONDS = 30 * 24 * 3600


def agreement(primary: Decision, shadow: Decision) -> bool:
    for question_id, answer in primary.answers.items():
        other = shadow.answers.get(question_id)
        if other is None or other.chosen != answer.chosen:
            return False
    return True


def brier(primary: Decision, shadow: Decision) -> float | None:
    """Mean Brier score over the questions both answered: the squared gap
    between the shadow's probability on each option and whether the
    rendered answer chose it. None when nothing overlaps."""
    scores: list[float] = []
    for question_id, answer in primary.answers.items():
        other = shadow.answers.get(question_id)
        if other is None or not other.probabilities:
            continue
        options = set(other.probabilities) | {answer.chosen}
        scores.append(
            sum(
                (
                    other.probabilities.get(option, 0.0)
                    - (1.0 if option == answer.chosen else 0.0)
                )
                ** 2
                for option in options
            )
        )
    return sum(scores) / len(scores) if scores else None


def record_shadow(
    redis: Redis, task: str
) -> Callable[[Decision | None, Decision | Exception | None], Awaitable[None]]:
    async def record(
        primary: Decision | None, shadow: Decision | Exception | None
    ) -> None:
        pipe = redis.pipeline()
        pipe.incr(TOTAL_KEY.format(task=task))
        pipe.expire(TOTAL_KEY.format(task=task), TTL_SECONDS)
        if isinstance(shadow, Exception) or shadow is None:
            pipe.incr(ERROR_KEY.format(task=task))
            pipe.expire(ERROR_KEY.format(task=task), TTL_SECONDS)
        elif primary is not None:
            if agreement(primary, shadow):
                pipe.incr(AGREE_KEY.format(task=task))
                pipe.expire(AGREE_KEY.format(task=task), TTL_SECONDS)
            pipe.incrby(LATENCY_KEY.format(task=task), shadow.latency_ms)
            pipe.expire(LATENCY_KEY.format(task=task), TTL_SECONDS)
            score = brier(primary, shadow)
            if score is not None:
                pipe.incrby(BRIER_KEY.format(task=task), round(score * 1000))
                pipe.expire(BRIER_KEY.format(task=task), TTL_SECONDS)
            sample: dict[str, Any] = {
                "primary": {k: v.chosen for k, v in primary.answers.items()},
                "shadow": {k: v.chosen for k, v in shadow.answers.items()},
                "probabilities": {
                    k: v.probabilities for k, v in shadow.answers.items()
                },
                "model": shadow.model,
            }
            pipe.lpush(SAMPLE_KEY.format(task=task), json.dumps(sample))
            pipe.ltrim(SAMPLE_KEY.format(task=task), 0, SAMPLE_MAX - 1)
            pipe.expire(SAMPLE_KEY.format(task=task), TTL_SECONDS)
        await pipe.execute()

    return record


async def shadow_report(redis: Redis, task: str) -> dict[str, Any]:
    total, agree, errors, latency, brier_milli = await redis.mget(
        [
            TOTAL_KEY.format(task=task),
            AGREE_KEY.format(task=task),
            ERROR_KEY.format(task=task),
            LATENCY_KEY.format(task=task),
            BRIER_KEY.format(task=task),
        ]
    )
    total_n, agree_n, errors_n = int(total or 0), int(agree or 0), int(errors or 0)
    answered = total_n - errors_n
    return {
        "task": task,
        "total": total_n,
        "agreement": round(agree_n / answered, 3) if answered else None,
        "error_rate": round(errors_n / total_n, 3) if total_n else None,
        "mean_latency_ms": round(int(latency or 0) / answered) if answered else None,
        # Lower is better; 0 means the shadow was sure of every rendered choice.
        "brier": round(int(brier_milli or 0) / 1000 / answered, 3)
        if answered
        else None,
    }
