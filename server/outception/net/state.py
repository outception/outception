"""The signal state every card carries: how fresh and how trustworthy its
data is. Worst state wins when cards merge. `unavailable` is HTTP 502 and
`loading` never reaches the wire; both exist so clients and the server
share one vocabulary.

The per-source failure record lives in Redis under `news:state:{id}`, written
on the refresh-failure branches of the fetch paths and cleared on success.
"""

import time
from dataclasses import dataclass
from enum import StrEnum

from outception.redis import Redis

STATE_KEY = "news:state:{id}"
# A record older than this is noise from a long-dead source; it expires.
STATE_TTL_SECONDS = 7 * 24 * 3600
# A source empty or failing for this long is `fallback`: both deck composers
# hide it until it recovers.
FALLBACK_AFTER_SECONDS = 24 * 3600


class SignalState(StrEnum):
    nominal = "nominal"
    loading = "loading"
    degraded = "degraded"
    stale = "stale"
    fallback = "fallback"
    unavailable = "unavailable"


# Higher is worse. `loading` sits below `degraded`: a card that is still
# loading is not yet known to be in trouble.
_SEVERITY: dict[SignalState, int] = {
    SignalState.nominal: 0,
    SignalState.loading: 1,
    SignalState.degraded: 2,
    SignalState.stale: 3,
    SignalState.fallback: 4,
    SignalState.unavailable: 5,
}


def worst(states: list[SignalState]) -> SignalState:
    """The state a merged card carries: the worst of its parts."""
    if not states:
        return SignalState.nominal
    return max(states, key=lambda state: _SEVERITY[state])


@dataclass(frozen=True)
class FailureRecord:
    fail_since: float  # epoch seconds of the first failure in the current run
    last_error_class: str  # transient, quota, auth, malformed, empty


async def note_failure(redis: Redis, source_id: str, error_class: str) -> None:
    """Record a refresh failure. The first failure in a run sets `fail_since`;
    later ones only update the class, so the run's age is preserved."""
    key = STATE_KEY.format(id=source_id)
    await redis.hsetnx(key, "fail_since", str(time.time()))
    await redis.hset(key, "last_error_class", error_class)
    await redis.expire(key, STATE_TTL_SECONDS)


async def clear_failure(redis: Redis, source_id: str) -> None:
    await redis.delete(STATE_KEY.format(id=source_id))


async def read_failure(redis: Redis, source_id: str) -> FailureRecord | None:
    raw = await redis.hgetall(STATE_KEY.format(id=source_id))
    if not raw:
        return None
    fail_since = raw.get("fail_since")
    if fail_since is None:
        return None
    try:
        return FailureRecord(
            fail_since=float(fail_since),
            last_error_class=str(raw.get("last_error_class", "transient")),
        )
    except ValueError:
        return None


def derive(
    *,
    age_ms: int | None,
    interval_ms: int,
    ttl_ms: int,
    failure: FailureRecord | None,
    now: float | None = None,
) -> SignalState:
    """The state of a cached entry.

    `age_ms` is how old the cached data is (None when nothing is cached).
    Fresh data within its interval is `nominal`. Data past its interval but
    within its TTL is `stale`. A refresh failure on top of cached data is
    `degraded` until the failure run is a day old, when it becomes
    `fallback`. No data at all is `unavailable`.
    """
    now = time.time() if now is None else now
    if failure is not None and now - failure.fail_since >= FALLBACK_AFTER_SECONDS:
        return SignalState.fallback
    if age_ms is None:
        return SignalState.unavailable
    if failure is not None:
        return SignalState.degraded
    if age_ms <= interval_ms:
        return SignalState.nominal
    if age_ms <= ttl_ms:
        return SignalState.stale
    return SignalState.stale
