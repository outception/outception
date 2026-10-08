"""The governor: keys, reservation, settlement, caps, cooldowns and the
served-model record. The only module that reads model keys.

Every call reserves an estimate against its lane's hourly and daily caps and
the global hourly cap in one Redis script, then settles the real cost
afterwards. A reservation that is never settled expires in five minutes and
the caps keep the estimate, which errs on the safe side.
"""

import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from outception.config import settings
from outception.net.provider import COOLDOWN_KEY, clamp_cooldown
from outception.net.provider import ProviderSpec as NetSpec
from outception.redis import Redis

from .classes import ErrorClass, ModelError
from .lanes import Consumer, Lane, caps, subcap

CAP_LANE_HOUR = "llm:cap:{lane}:h:{hour}"
CAP_LANE_DAY = "llm:cap:{lane}:d:{day}"
CAP_GLOBAL_HOUR = "llm:cap:global:h:{hour}"
CAP_PAID_DAY = "llm:cap:paid:d:{day}"
CAP_SUB_DAY = "llm:cap:{lane}:{consumer}:d:{day}"
RESERVE_KEY = "llm:reserve:{call_id}"
SERVED_KEY = "llm:served:{digest}"
PROMPT_KEY = "llm:prompt:{digest}"
DISABLED_KEY = "llm:disabled:{provider}"
RESERVE_TTL_SECONDS = 300
HOUR_TTL_SECONDS = 2 * 3600
DAY_TTL_SECONDS = 2 * 24 * 3600

_RESERVE_SCRIPT = (Path(__file__).parent / "scripts.lua").read_text()


def _hour(now: float) -> str:
    return datetime.fromtimestamp(now, tz=UTC).strftime("%Y%m%d%H")


def _day(now: float) -> str:
    return datetime.fromtimestamp(now, tz=UTC).strftime("%Y%m%d")


@dataclass(frozen=True)
class Reservation:
    call_id: str
    lane: Lane
    units: int
    provider: str
    consumer: Consumer | None = None


class CapExceeded(ModelError):
    """A lane, sub-cap, global or paid cap would be exceeded."""

    def __init__(self, provider: str, which: str) -> None:
        super().__init__(provider, ErrorClass.quota, detail=f"{which} cap")
        self.which = which


class LaneDisabled(ModelError):
    def __init__(self, provider: str) -> None:
        super().__init__(provider, ErrorClass.auth, detail="lane disabled")


def key_for(provider: str) -> str | None:
    """The first configured key for a provider id, or None. Keys are read
    here and nowhere else; the caller gets the value only to pass it to the
    provider's client and never logs it."""
    if provider in PAID_PROVIDERS and not settings.SUMMARY_MODEL:
        # The paid lane needs a model id from the host env as well as a key.
        return None
    single, many = _KEY_FIELDS.get(provider, (None, None))
    if many and getattr(settings, many, None):
        value = str(getattr(settings, many)).split(",")[0].strip()
        if value:
            return value
    if single and getattr(settings, single, None):
        return str(getattr(settings, single))
    return None


def keys_for(provider: str) -> list[str]:
    if provider in PAID_PROVIDERS and not settings.SUMMARY_MODEL:
        return []
    single, many = _KEY_FIELDS.get(provider, (None, None))
    found: list[str] = []
    if many and getattr(settings, many, None):
        found.extend(
            k.strip() for k in str(getattr(settings, many)).split(",") if k.strip()
        )
    if single and getattr(settings, single, None):
        found.append(str(getattr(settings, single)))
    return found


# provider id -> (single key field, comma-separated keys field)
_KEY_FIELDS: dict[str, tuple[str | None, str | None]] = {
    "gemini": ("GEMINI_API_KEY", "GEMINI_API_KEYS"),
    "groq": ("GROQ_API_KEY", "GROQ_API_KEYS"),
    "mistral": ("MISTRAL_API_KEY", "MISTRAL_API_KEYS"),
    "nvidia": ("NVIDIA_API_KEY", "NVIDIA_API_KEYS"),
    "ollama": ("OLLAMA_API_KEY", "OLLAMA_API_KEYS"),
    "cloudflare": ("CLOUDFLARE_AI_TOKEN", "CLOUDFLARE_AI_TOKENS"),
    "paid": ("ANTHROPIC_API_KEY", None),
    "own": ("ENGINE_API_KEY", None),
    "own-generation": ("OWN_GENERATION_API_KEY", None),
}

PAID_PROVIDERS = frozenset({"paid"})


class Governor:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis
        self._reserve = redis.register_script(_RESERVE_SCRIPT)

    # Availability

    def is_killed(self) -> bool:
        return bool(settings.LLM_DISABLED)

    def is_configured(self, provider: str) -> bool:
        if provider == "own":
            return bool(settings.ENGINE_URL)
        return bool(keys_for(provider))

    async def is_disabled(self, provider: str) -> bool:
        return bool(await self.redis.exists(DISABLED_KEY.format(provider=provider)))

    async def disable(self, provider: str) -> None:
        """An `auth` class disables the lane entry until a key rotation; the
        health reason `llm_lane_disabled` reports it."""
        await self.redis.set(DISABLED_KEY.format(provider=provider), "1")

    async def enable(self, provider: str) -> None:
        await self.redis.delete(DISABLED_KEY.format(provider=provider))

    async def cooldown_remaining(self, provider: str) -> int:
        ttl = await self.redis.ttl(COOLDOWN_KEY.format(provider=provider))
        return max(0, int(ttl)) if ttl and ttl > 0 else 0

    async def cool_down(
        self, provider: str, retry_after: float | None, spec: NetSpec | None = None
    ) -> int:
        spec = spec or NetSpec(id=provider, interval=0, fresh_for=0, stale_for=0)
        seconds = clamp_cooldown(spec, retry_after)
        await self.redis.set(COOLDOWN_KEY.format(provider=provider), "1", ex=seconds)
        return seconds

    async def available(self, provider: str) -> bool:
        if self.is_killed() or not self.is_configured(provider):
            return False
        if await self.is_disabled(provider):
            return False
        return not await self.cooldown_remaining(provider)

    # Usage

    async def used(self, lane: Lane, *, now: float | None = None) -> tuple[int, int]:
        now = time.time() if now is None else now
        hour = await self.redis.get(CAP_LANE_HOUR.format(lane=lane, hour=_hour(now)))
        day = await self.redis.get(CAP_LANE_DAY.format(lane=lane, day=_day(now)))
        return int(hour or 0), int(day or 0)

    async def paid_used(self, *, now: float | None = None) -> int:
        now = time.time() if now is None else now
        return int(await self.redis.get(CAP_PAID_DAY.format(day=_day(now))) or 0)

    # Reserve then settle

    async def reserve(
        self,
        lane: Lane,
        provider: str,
        units: int,
        *,
        consumer: Consumer | None = None,
        now: float | None = None,
    ) -> Reservation:
        if self.is_killed():
            raise LaneDisabled(provider)
        now = time.time() if now is None else now
        units = max(1, int(units))
        lane_caps = caps(lane)
        # Every cap is checked and charged inside one script, so two callers
        # racing for the last units of the paid day (or of a consumer's
        # share) cannot both read "room left" and both charge.
        sub_key = (
            CAP_SUB_DAY.format(lane=lane, consumer=consumer, day=_day(now))
            if consumer is not None
            else ""
        )
        paid_key = (
            CAP_PAID_DAY.format(day=_day(now)) if provider in PAID_PROVIDERS else ""
        )
        call_id = uuid.uuid4().hex
        outcome = int(
            await self._reserve(
                keys=[
                    CAP_LANE_HOUR.format(lane=lane, hour=_hour(now)),
                    CAP_LANE_DAY.format(lane=lane, day=_day(now)),
                    CAP_GLOBAL_HOUR.format(hour=_hour(now)),
                    RESERVE_KEY.format(call_id=call_id),
                    sub_key,
                    paid_key,
                ],
                args=[
                    units,
                    lane_caps.hourly,
                    lane_caps.daily,
                    settings.LLM_GLOBAL_HOURLY_CAP,
                    RESERVE_TTL_SECONDS,
                    HOUR_TTL_SECONDS,
                    DAY_TTL_SECONDS,
                    subcap(consumer) if consumer is not None else 0,
                    settings.LLM_PAID_DAILY_CAP,
                ],
            )
        )
        if outcome == 2:
            raise CapExceeded(provider, f"{consumer} sub")
        if outcome == 3:
            raise CapExceeded(provider, "paid daily")
        if outcome != 1:
            raise CapExceeded(provider, "lane or global")
        return Reservation(call_id, lane, units, provider, consumer)

    async def refresh(self, reservation: Reservation) -> None:
        """Called every few seconds while a reply streams, so a long stream
        does not lose its reservation."""
        await self.redis.expire(
            RESERVE_KEY.format(call_id=reservation.call_id), RESERVE_TTL_SECONDS
        )

    async def settle(
        self, reservation: Reservation, real_units: int, *, now: float | None = None
    ) -> None:
        """Charge the difference between the estimate and the real cost and
        forget the reservation. Settling at zero (a cancelled hedge) refunds
        the estimate."""
        now = time.time() if now is None else now
        delta = max(0, int(real_units)) - reservation.units
        if delta:
            for key in (
                CAP_LANE_HOUR.format(lane=reservation.lane, hour=_hour(now)),
                CAP_LANE_DAY.format(lane=reservation.lane, day=_day(now)),
                CAP_GLOBAL_HOUR.format(hour=_hour(now)),
            ):
                await self.redis.incrby(key, delta)
            if reservation.consumer is not None:
                await self.redis.incrby(
                    CAP_SUB_DAY.format(
                        lane=reservation.lane,
                        consumer=reservation.consumer,
                        day=_day(now),
                    ),
                    delta,
                )
            if reservation.provider in PAID_PROVIDERS:
                await self.redis.incrby(CAP_PAID_DAY.format(day=_day(now)), delta)
        await self.redis.delete(RESERVE_KEY.format(call_id=reservation.call_id))

    # Served-model record, for support

    async def record_served(self, digest: str, model: str) -> None:
        await self.redis.set(SERVED_KEY.format(digest=digest), model, ex=24 * 3600)

    async def served(self, digest: str) -> str | None:
        value = await self.redis.get(SERVED_KEY.format(digest=digest))
        return str(value) if value is not None else None
