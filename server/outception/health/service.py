"""Collect the health reasons from what the process can observe without
doing work: a `select 1`, a ping, the worker heartbeat key, the governor's
lane state, the engine's health route."""

import os
import time
from datetime import UTC, datetime
from typing import Any

from redis import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from outception.config import settings
from outception.net.provider import COOLDOWN_KEY
from outception.news.summaries.providers.chain import GENERATION_CHAINS
from outception.news.summaries.providers.governor import DISABLED_KEY, keys_for
from outception.news.summaries.providers.lanes import Lane
from outception.news.summaries.providers.own import OwnModel
from outception.postgres import AsyncSession
from outception.redis import Redis
from outception.worker.scheduler import (
    HEARTBEAT_STALENESS_SECONDS,
    SCHEDULER_HEARTBEAT_KEY,
)

from .reasons import CLEAR_AFTER_SECONDS, REASONS, Reason, Severity, status_for

SINCE_KEY = "health:since:{code}"
SEEN_KEY = "health:seen:{code}"
HEARTBEAT_GRACE_SECONDS = 90

STARTED_AT = time.time()


def _iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, tz=UTC).isoformat().replace("+00:00", "Z")


class HealthService:
    def __init__(
        self, session: AsyncSession, redis: Redis, *, engine: OwnModel | None = None
    ) -> None:
        self.session = session
        self.redis = redis
        self.engine = engine

    async def report(self, *, now: float | None = None) -> dict[str, Any]:
        now = time.time() if now is None else now
        observed: dict[str, str] = {}
        dependencies: dict[str, str] = {}

        try:
            await self.session.execute(text("SELECT 1"))
            dependencies["postgres"] = "ok"
        except SQLAlchemyError:
            dependencies["postgres"] = "down"
            observed["postgres_unreachable"] = "select 1 failed"

        redis_ok = True
        try:
            await self.redis.ping()
            dependencies["redis"] = "ok"
        except RedisError:
            redis_ok = False
            dependencies["redis"] = "down"
            observed["redis_unreachable"] = "ping failed"

        if redis_ok:
            dependencies["worker"] = await self._worker(observed, now)
            await self._llm(observed)
        else:
            dependencies["worker"] = "unknown"

        if settings.ENGINE_URL:
            engine = self.engine or OwnModel()
            if not await engine.health():
                observed["engine_unreachable"] = (
                    "the engine health route did not answer"
                )

        reasons = await self._with_clearing(observed, now, redis_ok)
        return {
            "status": status_for(reasons),
            "dependencies": dependencies,
            "runtime": {
                "version": os.environ.get("RELEASE_VERSION", "dev"),
                "started_at": _iso(STARTED_AT),
                "uptime_s": int(now - STARTED_AT),
            },
            "unhealthy_reasons": [reason.__dict__ for reason in reasons],
        }

    async def _worker(self, observed: dict[str, str], now: float) -> str:
        raw = await self.redis.get(SCHEDULER_HEARTBEAT_KEY)
        if raw is None:
            if now - STARTED_AT > HEARTBEAT_GRACE_SECONDS:
                observed["worker_heartbeat_stale"] = (
                    "no heartbeat after the start grace"
                )
                return "down"
            return "starting"
        try:
            age = now - float(raw)
        except ValueError:
            observed["worker_heartbeat_stale"] = "heartbeat unreadable"
            return "down"
        if age > HEARTBEAT_STALENESS_SECONDS:
            observed["worker_heartbeat_stale"] = f"heartbeat {int(age)} s old"
            return "down"
        return "ok"

    async def _llm(self, observed: dict[str, str]) -> None:
        if settings.LLM_DISABLED:
            observed["llm_lane_disabled"] = "LLM_DISABLED is set"
            return
        for lane, chain in GENERATION_CHAINS.items():
            configured = [provider for provider in chain if keys_for(provider)]
            if not configured:
                continue
            disabled = [
                p
                for p in configured
                if await self.redis.exists(DISABLED_KEY.format(provider=p))
            ]
            if disabled and len(disabled) == len(configured):
                observed["llm_lane_disabled"] = f"{lane} lane: every provider disabled"
                continue
            cooling = [
                p
                for p in configured
                if p not in disabled
                and await self.redis.exists(COOLDOWN_KEY.format(provider=p))
            ]
            if len(cooling) + len(disabled) == len(configured):
                observed["llm_chain_exhausted"] = f"{lane} lane: all providers cooling"
        _ = Lane

    async def _with_clearing(
        self, observed: dict[str, str], now: float, redis_ok: bool
    ) -> list[Reason]:
        """Attach `since` to each observed reason and keep `info` and
        `warning` reasons reported for a short while after their condition
        clears, so a flapping condition reads as one episode."""
        reasons: list[Reason] = []
        for code, spec in REASONS.items():
            detail = observed.get(code)
            if detail is None and not redis_ok:
                continue
            since_key = SINCE_KEY.format(code=code)
            seen_key = SEEN_KEY.format(code=code)
            if detail is not None:
                if redis_ok:
                    since_raw = await self.redis.get(since_key)
                    if since_raw is None:
                        await self.redis.set(since_key, str(now))
                        since = now
                    else:
                        since = float(since_raw)
                    await self.redis.set(seen_key, str(now), ex=CLEAR_AFTER_SECONDS)
                else:
                    since = now
                reasons.append(
                    Reason(
                        code,
                        spec.subsystem,
                        spec.severity,
                        detail,
                        spec.remedy,
                        _iso(since),
                    )
                )
                continue
            if spec.severity == Severity.critical:
                await self.redis.delete(since_key, seen_key)
                continue
            seen_raw = await self.redis.get(seen_key)
            if seen_raw is None:
                await self.redis.delete(since_key)
                continue
            since_raw = await self.redis.get(since_key)
            since = float(since_raw) if since_raw else float(seen_raw)
            reasons.append(
                Reason(
                    code,
                    spec.subsystem,
                    spec.severity,
                    "clearing",
                    spec.remedy,
                    _iso(since),
                )
            )
        return reasons
