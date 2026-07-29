"""Additional free-tier LLM providers (Groq, Mistral, Cerebras) behind one
discipline.

Second line of free capacity after the Gemini fleet: when Gemini is benched,
minute-full, or out of daily quota, these OpenAI-compatible endpoints pick up
translations and summaries before a single paid call is made. Same rules as
gemini.py - per-endpoint per-minute metering, failure-classified benching
(seconds for a burst, until reset for spent quota, long for a dead key), and
round-robin so quota drains evenly - because those rules are what keeps a
free tier usable all day instead of being burned down by 9am.

Endpoints are built from settings: GROQ_API_KEY(S), MISTRAL_API_KEY(S) and
CEREBRAS_API_KEY(S), comma-separated for multiple keys. A provider with no
key simply isn't in the pool; nothing else changes.
"""

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import httpx
import structlog

from outception.config import settings
from outception.redis import Redis

log = structlog.get_logger()

_COOLDOWN_KEY = "news:freellm:cd:{id}"
_RPM_KEY = "news:freellm:rpm:{id}:{minute}"
_REJECTED_KEY = "news:freellm:rejected:{id}"
_ROUND_ROBIN_KEY = "news:freellm:rr"

_MAX_COOLDOWN_SECONDS = 60 * 60
_BURST_COOLDOWN_SECONDS = 30
_OUTAGE_COOLDOWN_SECONDS = 60
_TIMEOUT_COOLDOWN_SECONDS = 10
# Providers reset daily quotas on their own clocks (Groq's is rolling); an
# hourly re-probe is the same compromise gemini.py makes for a mis-read.
_DAILY_RESET_HOUR_UTC = 0

# Matched against the STRUCTURED error code/type fields only, never the raw
# body: providers sometimes echo request content into validation messages, and
# a paywalled article that literally contains "payment required" must not
# bench a healthy key for the day.
_DEAD_KEY_MARKERS = (
    "invalid_api_key",
    "invalid api key",
    "api key not valid",
    "account_deactivated",
    "permission_denied",
)


@dataclass(frozen=True)
class Endpoint:
    """One (provider, key) pair. `id` names it in Redis and logs - never the
    key itself (`repr=False` keeps it out of any future object log too)."""

    id: str
    provider: str
    url: str
    model: str
    key: str = field(repr=False)
    rpm: int = 0


def _split(raw: str | None) -> list[str]:
    return [key.strip() for key in (raw or "").split(",") if key.strip()]


def endpoints() -> list[Endpoint]:
    pool: list[Endpoint] = []
    for i, key in enumerate(_split(settings.GROQ_API_KEYS or settings.GROQ_API_KEY)):
        pool.append(
            Endpoint(
                id=f"groq:{i}",
                provider="groq",
                url="https://api.groq.com/openai/v1/chat/completions",
                model=settings.GROQ_MODEL,
                key=key,
                rpm=settings.GROQ_RPM_CAP,
            )
        )
    for i, key in enumerate(
        _split(settings.MISTRAL_API_KEYS or settings.MISTRAL_API_KEY)
    ):
        pool.append(
            Endpoint(
                id=f"mistral:{i}",
                provider="mistral",
                url="https://api.mistral.ai/v1/chat/completions",
                model=settings.MISTRAL_MODEL,
                key=key,
                rpm=settings.MISTRAL_RPM_CAP,
            )
        )
    for i, key in enumerate(
        _split(settings.CEREBRAS_API_KEYS or settings.CEREBRAS_API_KEY)
    ):
        pool.append(
            Endpoint(
                id=f"cerebras:{i}",
                provider="cerebras",
                url="https://api.cerebras.ai/v1/chat/completions",
                model=settings.CEREBRAS_MODEL,
                key=key,
                rpm=settings.CEREBRAS_RPM_CAP,
            )
        )
    return pool


def configured() -> bool:
    return bool(endpoints())


async def available(redis: Redis) -> bool:
    """Whether any endpoint could serve right now (not benched). Reserves
    nothing - a prognosis, mirroring gemini.available."""
    pool = endpoints()
    if not pool:
        return False
    benched = await redis.mget([_COOLDOWN_KEY.format(id=e.id) for e in pool])
    return any(value is None for value in benched)


async def acquire(redis: Redis) -> Endpoint | None:
    """An endpoint that is neither benched nor minute-full; None when every
    endpoint is unusable right now. Round-robin, like the Gemini pool."""
    pool = endpoints()
    if not pool:
        return None
    minute = datetime.now(UTC).strftime("%Y%m%d%H%M")
    start = int(await redis.incr(_ROUND_ROBIN_KEY)) % len(pool)
    benched = await redis.mget([_COOLDOWN_KEY.format(id=e.id) for e in pool])
    for step in range(len(pool)):
        index = (start + step) % len(pool)
        if benched[index] is not None:
            continue
        endpoint = pool[index]
        rpm = _RPM_KEY.format(id=endpoint.id, minute=minute)
        count = await redis.incr(rpm)
        if count == 1:
            await redis.expire(rpm, 120)
        if count <= endpoint.rpm:
            return endpoint
        await redis.decr(rpm)
    return None


def _seconds_until_daily_reset(now: datetime | None = None) -> int:
    now = now or datetime.now(UTC)
    reset = now.replace(hour=_DAILY_RESET_HOUR_UTC, minute=0, second=0, microsecond=0)
    if reset <= now:
        reset += timedelta(days=1)
    return int((reset - now).total_seconds())


def _rejects_key(exc: BaseException) -> bool:
    if not isinstance(exc, httpx.HTTPStatusError):
        return False
    status = exc.response.status_code
    # 401/402 speak for themselves: the key (or the account behind it) is the
    # problem, whatever the body says.
    if status in (401, 402):
        return True
    if status not in (400, 403):
        return False
    try:
        error = exc.response.json().get("error") or {}
    except (ValueError, AttributeError):
        return False
    if not isinstance(error, dict):
        return False
    fields = " ".join(str(error.get(name) or "") for name in ("code", "type")).lower()
    return any(marker in fields for marker in _DEAD_KEY_MARKERS)


def cooldown_seconds(exc: BaseException) -> int | None:
    """How long to bench an endpoint after *exc*; None when the failure says
    nothing about capacity and the next call may retry."""
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if _rejects_key(exc):
            return _MAX_COOLDOWN_SECONDS
        if status == 429:
            body = exc.response.text[:4000]
            retry_after = exc.response.headers.get("retry-after")
            if retry_after and retry_after.isdigit():
                return max(5, min(_MAX_COOLDOWN_SECONDS, int(retry_after)))
            if re.search(r"per day|daily|RPD|TPD", body, re.IGNORECASE):
                return max(
                    _BURST_COOLDOWN_SECONDS,
                    min(_MAX_COOLDOWN_SECONDS, _seconds_until_daily_reset()),
                )
            return _BURST_COOLDOWN_SECONDS
        return _OUTAGE_COOLDOWN_SECONDS
    if isinstance(exc, httpx.TimeoutException):
        return _TIMEOUT_COOLDOWN_SECONDS
    if isinstance(exc, httpx.HTTPError):
        return _OUTAGE_COOLDOWN_SECONDS
    return None


async def note_failure(redis: Redis, endpoint: Endpoint, exc: BaseException) -> None:
    """Bench *endpoint* for as long as *exc* implies (see gemini.note_failure
    for the reasoning on repeats of a dead key)."""
    seconds = cooldown_seconds(exc)
    if _rejects_key(exc):
        rejected_key = _REJECTED_KEY.format(id=endpoint.id)
        rejections = await redis.incr(rejected_key)
        if rejections == 1:
            await redis.expire(rejected_key, _seconds_until_daily_reset())
        else:
            seconds = _seconds_until_daily_reset()
        log.warning(
            "news.free_llm_key_rejected",
            endpoint=endpoint.id,
            rejections=rejections,
            benched_for=seconds,
        )
    if seconds:
        await redis.set(_COOLDOWN_KEY.format(id=endpoint.id), "1", ex=seconds)


def _body(
    endpoint: Endpoint, system: str, user: str, *, stream: bool
) -> dict[str, object]:
    body: dict[str, object] = {
        "model": endpoint.model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_completion_tokens": 500,
        "stream": stream,
    }
    if "gpt-oss" in endpoint.model:
        # gpt-oss is a reasoning model (served by Groq and Cerebras): without
        # this it spends its token budget thinking and returns truncated (or
        # empty) content.
        body["reasoning_effort"] = "low"
    return body


_client = httpx.AsyncClient(timeout=30.0)


async def generate(system: str, user: str, endpoint: Endpoint) -> str:
    """One completion. Raises httpx errors for note_failure to classify."""
    response = await _client.post(
        endpoint.url,
        headers={
            "Authorization": f"Bearer {endpoint.key}",
            "content-type": "application/json",
        },
        json=_body(endpoint, system, user, stream=False),
    )
    response.raise_for_status()
    data = response.json()
    choices = data.get("choices") or []
    message = (choices[0].get("message") or {}) if choices else {}
    return (message.get("content") or "").strip()
