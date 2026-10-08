"""One provider's key pool: several free-tier keys used round-robin, each
with its own bench (burst cooldown or spent daily quota), its own
per-minute meter and, where the free allowance is metered in something
other than requests, our own per-day ceiling. Round-robin so quota drains
evenly across the pool; drain-in-order spent the first keys by mid-day
while the tail sat idle.

Keys never appear in Redis key names or logs: a slot is addressed by its
index in the configured list, so a dead account can be found without
going key by key."""

import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import structlog

from outception.redis import Redis

log = structlog.get_logger()

COOLDOWN_KEY = "llm:key:cd:{provider}:{i}"
RPM_KEY = "llm:key:rpm:{provider}:{i}:{minute}"
RPD_KEY = "llm:key:rpd:{provider}:{i}:{day}"
REJECTED_KEY = "llm:key:rejected:{provider}:{i}"
ROUND_ROBIN_KEY = "llm:key:rr:{provider}"


@dataclass(frozen=True)
class Slot:
    index: int
    key: str = field(repr=False)


def seconds_until_reset(reset_hour_utc: int, now: datetime | None = None) -> int:
    """Seconds until the provider's daily quota rolls over."""
    now = now or datetime.now(UTC)
    reset = now.replace(hour=reset_hour_utc, minute=0, second=0, microsecond=0)
    if reset <= now:
        reset += timedelta(days=1)
    return int((reset - now).total_seconds())


class KeyPool:
    def __init__(
        self,
        redis: Redis,
        provider: str,
        keys: list[str],
        *,
        rpm: int = 0,
        rpd: int = 0,
        reset_hour_utc: int = 0,
    ) -> None:
        self.redis = redis
        self.provider = provider
        self.keys = [key for key in keys if key]
        self.rpm = rpm
        self.rpd = rpd
        self.reset_hour_utc = reset_hour_utc

    def __len__(self) -> int:
        return len(self.keys)

    @property
    def configured(self) -> bool:
        return bool(self.keys)

    def _cooldown_keys(self) -> list[str]:
        return [
            COOLDOWN_KEY.format(provider=self.provider, i=i)
            for i in range(len(self.keys))
        ]

    async def available(self) -> bool:
        """Whether any key could serve right now (not benched). Reserves
        nothing: a prognosis for the availability check. One MGET."""
        if not self.keys:
            return False
        benched = await self.redis.mget(self._cooldown_keys())
        return any(value is None for value in benched)

    async def acquire(self, *, now: float | None = None) -> Slot | None:
        """A key that is neither benched nor minute-full (nor past its day
        ceiling), or None when every key is unusable right now. The probe
        itself never inflates a full key's meter."""
        if not self.keys:
            return None
        stamp = datetime.fromtimestamp(time.time() if now is None else now, tz=UTC)
        minute = stamp.strftime("%Y%m%d%H%M")
        start = int(
            await self.redis.incr(ROUND_ROBIN_KEY.format(provider=self.provider))
        )
        start %= len(self.keys)
        benched = await self.redis.mget(self._cooldown_keys())
        for step in range(len(self.keys)):
            index = (start + step) % len(self.keys)
            if benched[index] is not None:
                continue
            if self.rpm:
                rpm = RPM_KEY.format(provider=self.provider, i=index, minute=minute)
                count = int(await self.redis.incr(rpm))
                if count == 1:
                    await self.redis.expire(rpm, 120)
                if count > self.rpm:
                    await self.redis.decr(rpm)
                    continue
            if self.rpd:
                rpd = RPD_KEY.format(provider=self.provider, i=index, day=minute[:8])
                daily = int(await self.redis.incr(rpd))
                if daily == 1:
                    await self.redis.expire(rpd, 2 * 24 * 60 * 60)
                if daily > self.rpd:
                    await self.redis.decr(rpd)
                    if self.rpm:
                        await self.redis.decr(
                            RPM_KEY.format(
                                provider=self.provider, i=index, minute=minute
                            )
                        )
                    continue
            return Slot(index, self.keys[index])
        return None

    async def bench(self, index: int, seconds: int) -> None:
        await self.redis.set(
            COOLDOWN_KEY.format(provider=self.provider, i=index), "1", ex=seconds
        )

    async def note_failure(
        self, index: int, seconds: int | None, *, rejected: bool = False
    ) -> int | None:
        """Bench the key for as long as the failure implies. A rejected key
        (suspended project, revoked key) is benched an hour the first time,
        in case the verdict is wrong, and until the daily reset on the
        repeat: retrying a suspended account all day is the traffic that
        provokes a suspension."""
        if rejected:
            rejected_key = REJECTED_KEY.format(provider=self.provider, i=index)
            rejections = int(await self.redis.incr(rejected_key))
            until_reset = seconds_until_reset(self.reset_hour_utc)
            if rejections == 1:
                await self.redis.expire(rejected_key, until_reset)
            else:
                seconds = until_reset
            log.warning(
                "llm.key_rejected",
                provider=self.provider,
                index=index,
                rejections=rejections,
                benched_for=seconds,
            )
        if seconds:
            await self.bench(index, seconds)
        return seconds
