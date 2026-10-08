"""The provider robustness toolkit: one set of behaviours for every upstream
the server talks to (feeds, tables, live signals, weather, model lanes).

Redis-backed, because the API and the worker are separate processes:

- single-flight: one upstream call per key at a time
- adaptive TTL: a provider that reports remaining quota sets its own window
- cooldown: on 429 or 5xx, honour Retry-After within a per-provider range
- serve-stale: a read past freshness returns the value tagged `stale`
- daily budget: upstream attempts per UTC day, never cache hits
- negative cache: "answered with nothing" is cached briefly
- timeout retry: one retry on timeout, none on 4xx
- byte cap: oversize bodies are a provider error, not a crash

Every provider declares a `ProviderSpec` and takes an injected `fetch`, so
the whole module is tested without network.
"""

import asyncio
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from enum import StrEnum
from typing import Generic, TypeVar

from outception.redis import Redis

from .state import SignalState

T = TypeVar("T")

FLIGHT_KEY = "net:flight:{key}"
TTL_KEY = "net:ttl:{provider}"
COOLDOWN_KEY = "net:cooldown:{provider}"
BUDGET_KEY = "net:budget:{provider}:{day}"
NEGATIVE_KEY = "net:neg:{key}"

NEGATIVE_TTL_SECONDS = 30
FLIGHT_TTL_SECONDS = 60
FLIGHT_POLL_SECONDS = 0.1

# Compare-and-delete: the flight key goes only when it still carries the
# releasing holder's token.
_RELEASE_FLIGHT = (
    "if redis.call('GET', KEYS[1]) == ARGV[1] then"
    " return redis.call('DEL', KEYS[1]) end return 0"
)


class ProviderError(Exception):
    """An upstream answered badly. `status` carries the HTTP status when
    there was one; `retry_after` the parsed Retry-After in seconds."""

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        retry_after: float | None = None,
        timeout: bool = False,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.retry_after = retry_after
        self.timeout = timeout


class Status(StrEnum):
    """Why a value was served the way it was. Internal; the wire carries
    the signal state."""

    fresh = "fresh"
    cached = "cached"
    cooling = "cooling"
    budget = "budget"
    negative = "negative"
    failed = "failed"


@dataclass(frozen=True)
class ProviderSpec:
    id: str
    interval: int  # ms between refreshes under normal quota
    fresh_for: int  # ms a value counts as fresh
    stale_for: int  # ms a value is still served past freshness
    budget_per_day: int | None = None  # upstream attempts per UTC day
    cooldown_range: tuple[int, int] = (30, 900)  # seconds, clamp for Retry-After
    byte_cap: int = 2 * 1024 * 1024
    terms: str | None = None  # attribution line for the credits drawer


@dataclass(frozen=True)
class Fetched(Generic[T]):  # noqa: UP046 # keep the explicit TypeVar for the covariant payload
    value: T | None
    state: SignalState
    status: Status
    fetched_at: float | None  # epoch seconds of the value's own fetch


# Adaptive TTL: the share of daily quota left decides how often a provider
# is asked. The multiplier scales the declared interval.
QUOTA_STEPS: tuple[tuple[float, float], ...] = (
    (0.5, 1.0),  # plenty: declared interval
    (0.25, 2.0),  # normal
    (0.1, 4.0),  # low
    (0.0, 12.0),  # critical
)


def interval_for_quota(spec: ProviderSpec, remaining_share: float) -> int:
    for floor, multiplier in QUOTA_STEPS:
        if remaining_share >= floor:
            return int(spec.interval * multiplier)
    return int(spec.interval * QUOTA_STEPS[-1][1])


def parse_retry_after(value: str | None, *, now: float | None = None) -> float | None:
    """Retry-After as seconds, from either an integer or an HTTP date."""
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    if value.isdigit():
        return float(value)
    try:
        when = parsedate_to_datetime(value)
    except TypeError, ValueError, IndexError:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    now = time.time() if now is None else now
    return max(0.0, when.timestamp() - now)


def clamp_cooldown(spec: ProviderSpec, seconds: float | None) -> int:
    low, high = spec.cooldown_range
    if seconds is None:
        return low
    return int(min(max(seconds, low), high))


def _day(now: float) -> str:
    return datetime.fromtimestamp(now, tz=UTC).strftime("%Y%m%d")


class Toolkit:
    """The toolkit over one Redis connection. One instance per process."""

    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    # Cooldown

    async def cooldown_remaining(self, provider: str) -> int:
        ttl = await self.redis.ttl(COOLDOWN_KEY.format(provider=provider))
        return max(0, int(ttl)) if ttl and ttl > 0 else 0

    async def set_cooldown(self, spec: ProviderSpec, retry_after: float | None) -> int:
        seconds = clamp_cooldown(spec, retry_after)
        await self.redis.set(COOLDOWN_KEY.format(provider=spec.id), "1", ex=seconds)
        return seconds

    async def clear_cooldown(self, provider: str) -> None:
        await self.redis.delete(COOLDOWN_KEY.format(provider=provider))

    # Budget

    async def budget_spent(self, provider: str, *, now: float | None = None) -> int:
        now = time.time() if now is None else now
        raw = await self.redis.get(BUDGET_KEY.format(provider=provider, day=_day(now)))
        return int(raw or 0)

    async def budget_available(
        self, spec: ProviderSpec, *, now: float | None = None
    ) -> bool:
        if spec.budget_per_day is None:
            return True
        return await self.budget_spent(spec.id, now=now) < spec.budget_per_day

    async def charge_budget(
        self, spec: ProviderSpec, *, now: float | None = None
    ) -> int:
        now = time.time() if now is None else now
        key = BUDGET_KEY.format(provider=spec.id, day=_day(now))
        count = await self.redis.incr(key)
        if count == 1:
            await self.redis.expire(key, 2 * 24 * 3600)
        return int(count)

    async def remaining_share(
        self, spec: ProviderSpec, *, now: float | None = None
    ) -> float:
        if spec.budget_per_day is None:
            return 1.0
        spent = await self.budget_spent(spec.id, now=now)
        return max(0.0, 1.0 - spent / spec.budget_per_day)

    # Adaptive TTL

    async def interval(self, spec: ProviderSpec) -> int:
        raw = await self.redis.get(TTL_KEY.format(provider=spec.id))
        if raw is None:
            return spec.interval
        try:
            return int(raw)
        except ValueError:
            return spec.interval

    async def note_quota(self, spec: ProviderSpec, remaining_share: float) -> int:
        interval = interval_for_quota(spec, remaining_share)
        await self.redis.set(
            TTL_KEY.format(provider=spec.id), str(interval), ex=24 * 3600
        )
        return interval

    # Negative cache

    async def is_negative(self, key: str) -> bool:
        return bool(await self.redis.exists(NEGATIVE_KEY.format(key=key)))

    async def set_negative(self, key: str) -> None:
        await self.redis.set(NEGATIVE_KEY.format(key=key), "1", ex=NEGATIVE_TTL_SECONDS)

    # Single-flight

    async def single_flight(
        self,
        key: str,
        work: Callable[[], Awaitable[T]],
        *,
        wait: Callable[[], Awaitable[T | None]] | None = None,
        timeout: float = FLIGHT_TTL_SECONDS,
    ) -> T | None:
        """Run `work` if nobody else is running it for `key`; otherwise wait
        for the holder and return what `wait` reads back (None when the
        holder gave up). The lock expires on its own so a dead holder never
        wedges a key."""
        flight_key = FLIGHT_KEY.format(key=key)
        token = uuid.uuid4().hex
        acquired = await self.redis.set(flight_key, token, nx=True, ex=int(timeout))
        if acquired:
            try:
                return await work()
            finally:
                # Release only our own flight: if the TTL ran out mid-work
                # and another caller holds the key now, a plain delete
                # would free theirs under them.
                await self.redis.eval(_RELEASE_FLIGHT, 1, flight_key, token)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            await asyncio.sleep(FLIGHT_POLL_SECONDS)
            if not await self.redis.exists(flight_key):
                return await wait() if wait is not None else None
        return await wait() if wait is not None else None

    # The whole pattern

    async def fetch(
        self,
        spec: ProviderSpec,
        key: str,
        fetch: Callable[[], Awaitable[T | None]],
        *,
        cached: T | None,
        cached_at: float | None,
        now: float | None = None,
        reload: Callable[[], Awaitable[tuple[T | None, float | None]]] | None = None,
    ) -> Fetched[T]:
        """Serve `key` for `spec`: the cached value when fresh, otherwise one
        refresh behind single-flight, honouring cooldown and budget, with
        the cached value served stale when the refresh cannot happen.

        `fetch` returns None for "answered with nothing" (negatively cached)
        and raises `ProviderError` for a bad answer or a timeout. `reload`
        re-reads the cache (value, written-at): a caller that waited on
        another's refresh serves what that refresh wrote, not the value it
        walked in with.
        """
        now = time.time() if now is None else now
        interval = await self.interval(spec)
        age_ms = int((now - cached_at) * 1000) if cached_at is not None else None

        if age_ms is not None and age_ms <= interval:
            return Fetched(cached, SignalState.nominal, Status.cached, cached_at)
        if await self.is_negative(key):
            state = SignalState.stale if cached is not None else SignalState.unavailable
            return Fetched(cached, state, Status.negative, cached_at)

        stale_state = (
            SignalState.stale
            if cached is not None and age_ms is not None and age_ms <= spec.stale_for
            else SignalState.unavailable
        )
        if await self.cooldown_remaining(spec.id):
            state = SignalState.degraded if cached is not None else stale_state
            return Fetched(cached, state, Status.cooling, cached_at)
        if not await self.budget_available(spec, now=now):
            return Fetched(cached, stale_state, Status.budget, cached_at)

        async def attempt() -> Fetched[T]:
            await self.charge_budget(spec, now=now)
            try:
                value = await self._fetch_with_retry(fetch)
            except ProviderError as error:
                if error.status is not None and (
                    error.status == 429 or error.status >= 500
                ):
                    await self.set_cooldown(spec, error.retry_after)
                    state = SignalState.degraded if cached is not None else stale_state
                    return Fetched(cached, state, Status.cooling, cached_at)
                state = SignalState.degraded if cached is not None else stale_state
                return Fetched(cached, state, Status.failed, cached_at)
            if value is None:
                await self.set_negative(key)
                state = (
                    SignalState.stale if cached is not None else SignalState.unavailable
                )
                return Fetched(cached, state, Status.negative, cached_at)
            return Fetched(value, SignalState.nominal, Status.fresh, now)

        async def wait_for_holder() -> Fetched[T] | None:
            if reload is None:
                return None
            value, written_at = await reload()
            if written_at is None or (
                cached_at is not None and written_at <= cached_at
            ):
                return None
            return Fetched(value, SignalState.nominal, Status.cached, written_at)

        result = await self.single_flight(key, attempt, wait=wait_for_holder)
        if result is None:
            return Fetched(cached, stale_state, Status.cached, cached_at)
        return result

    async def _fetch_with_retry(
        self, fetch: Callable[[], Awaitable[T | None]]
    ) -> T | None:
        try:
            return await fetch()
        except ProviderError as error:
            if not error.timeout:
                raise
        return await fetch()
