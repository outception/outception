"""Gemini free-tier discipline shared by translation and summaries.

Several free-tier keys (one per Google account) are used in order: each carries
its own per-minute and per-day quota, so when one is spent the next takes over,
and only when all are spent does the paid backup run. Failures are classified —
a per-minute burst benches a key for seconds, an exhausted daily quota until
Google's reset — and calls are metered per minute per key.
"""

import re
from datetime import UTC, datetime, timedelta

import httpx
import structlog

from outception.config import settings
from outception.redis import Redis

log = structlog.get_logger()

# Per-key: benched (burst cooldown or spent daily quota) and this minute's calls.
_COOLDOWN_KEY = "news:gemini:cd:{i}"
_RPM_KEY = "news:gemini:rpm:{i}:{minute}"
_REJECTED_KEY = "news:gemini:rejected:{i}"
# Google resets free-tier daily quotas at midnight Pacific (07:00/08:00 UTC).
_DAILY_RESET_HOUR_UTC = 8
_MAX_COOLDOWN_SECONDS = 60 * 60
_BURST_COOLDOWN_SECONDS = 30
_OUTAGE_COOLDOWN_SECONDS = 60
# One slow answer is usually one slow answer, not an outage: a full minute on
# the bench after a single timeout leaves the wall in originals for that long.
_TIMEOUT_COOLDOWN_SECONDS = 10
# A key whose project is suspended, or that has been revoked, answers instantly
# and forever — benching it for a minute means retrying it all day, spending a
# pool slot and a round trip each time. These are Google's markers for that.
_DEAD_KEY_MARKERS = (
    "api_key_invalid",
    "api key not valid",
    "consumer_suspended",
    "permission_denied",
    "service_disabled",
    "has been suspended",
)


def keys() -> list[str]:
    """The configured keys, in priority order. GEMINI_API_KEYS (comma
    separated, one per account) wins; GEMINI_API_KEY stays as the single-key
    fallback."""
    raw = settings.GEMINI_API_KEYS or settings.GEMINI_API_KEY or ""
    return [key.strip() for key in raw.split(",") if key.strip()]


def configured() -> bool:
    return bool(keys())


def _seconds_until_daily_reset(now: datetime | None = None) -> int:
    now = now or datetime.now(UTC)
    reset = now.replace(hour=_DAILY_RESET_HOUR_UTC, minute=0, second=0, microsecond=0)
    if reset <= now:
        reset += timedelta(days=1)
    return int((reset - now).total_seconds())


def _rejects_key(exc: BaseException) -> bool:
    """Whether *exc* is Google rejecting the key itself — suspended project,
    revoked key, API disabled — rather than a capacity or transport problem."""
    if not isinstance(exc, httpx.HTTPStatusError):
        return False
    if exc.response.status_code not in (400, 401, 403):
        return False
    body = exc.response.text[:4000].lower()
    return any(marker in body for marker in _DEAD_KEY_MARKERS)


def cooldown_seconds(exc: BaseException) -> int | None:
    """How long to bench a key after *exc*; None when the failure says nothing
    about capacity (an empty or unparsable reply) and the next call may retry."""
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        body = exc.response.text[:4000]
        if _rejects_key(exc):
            # First time, an hour only: if the classification is ever wrong, a
            # healthy key loses an hour rather than a day. `note_failure`
            # escalates on the repeat, once the verdict is not a one-off.
            return _MAX_COOLDOWN_SECONDS
        if status == 429:
            if re.search(r"PerDay|per day|daily", body, re.IGNORECASE):
                # Re-probe hourly anyway: the quota may have been a mis-read.
                return max(
                    _BURST_COOLDOWN_SECONDS,
                    min(_MAX_COOLDOWN_SECONDS, _seconds_until_daily_reset()),
                )
            match = re.search(r'"retryDelay":\s*"(\d+)(?:\.\d+)?s"', body)
            if match:
                return max(5, min(_MAX_COOLDOWN_SECONDS, int(match.group(1))))
            return _BURST_COOLDOWN_SECONDS
        return _OUTAGE_COOLDOWN_SECONDS
    if isinstance(exc, httpx.TimeoutException):
        return _TIMEOUT_COOLDOWN_SECONDS
    if isinstance(exc, httpx.HTTPError):
        return _OUTAGE_COOLDOWN_SECONDS
    return None


async def available(redis: Redis) -> bool:
    """Whether any key could serve right now (not benched). Reserves nothing —
    a prognosis for the summary availability check. One MGET, because this runs
    on the tap path once per configured key."""
    total = len(keys())
    if not total:
        return False
    benched = await redis.mget(
        [_COOLDOWN_KEY.format(i=index) for index in range(total)]
    )
    return any(value is None for value in benched)


_ROUND_ROBIN_KEY = "news:gemini:rr"


async def acquire(redis: Redis, per_minute: int) -> tuple[int, str] | None:
    """A key that is neither benched nor minute-full, as (index, key); None
    when every key is unusable right now. Calls round-robin across the pool so
    daily quota drains evenly on every key — with drain-in-order the first
    keys were spent by mid-day while the tail sat idle, and afternoon bursts
    ran on a shrinking pool."""
    pool = keys()
    if not pool:
        return None
    minute = datetime.now(UTC).strftime("%Y%m%d%H%M")
    start = int(await redis.incr(_ROUND_ROBIN_KEY)) % len(pool)
    # One MGET for the whole pool's bench state, not a GET per key — this
    # precedes every model call, and a mostly-benched pool cost 1+2N trips.
    benched = await redis.mget([_COOLDOWN_KEY.format(i=i) for i in range(len(pool))])
    for step in range(len(pool)):
        index = (start + step) % len(pool)
        if benched[index] is not None:
            continue
        rpm = _RPM_KEY.format(i=index, minute=minute)
        count = await redis.incr(rpm)
        if count == 1:
            await redis.expire(rpm, 120)
        if count <= per_minute:
            return index, pool[index]
        # The probe itself must not inflate a full key's minute counter —
        # rejected probes kept pushing the count further past the cap.
        await redis.decr(rpm)
    return None


async def note_failure(redis: Redis, index: int, exc: BaseException) -> int | None:
    """Bench key *index* for as long as *exc* implies — seconds for a burst,
    until the daily reset for spent quota."""
    seconds = cooldown_seconds(exc)
    if _rejects_key(exc):
        # A suspended or revoked key is rejected the same way every time, so
        # after the first repeat stop probing it until the quotas roll over:
        # retrying a suspended project all day is exactly the traffic that
        # provokes a suspension in the first place. One probe after the reset
        # is enough to notice the key coming back. The index names the position
        # in GEMINI_API_KEYS, so a dead account can be found without going key
        # by key.
        rejected_key = _REJECTED_KEY.format(i=index)
        rejections = await redis.incr(rejected_key)
        if rejections == 1:
            await redis.expire(rejected_key, _seconds_until_daily_reset())
        else:
            seconds = _seconds_until_daily_reset()
        log.warning(
            "news.gemini_key_rejected",
            index=index,
            rejections=rejections,
            benched_for=seconds,
        )
    if seconds:
        await redis.set(_COOLDOWN_KEY.format(i=index), "1", ex=seconds)
    return seconds
