import time

import pytest
from httpx import AsyncClient
from pytest_mock import MockerFixture

from outception.config import settings
from outception.health import service as health_service
from outception.health.service import HealthService
from outception.news.summaries.providers.governor import DISABLED_KEY
from outception.postgres import AsyncSession
from outception.redis import Redis
from outception.worker.scheduler import SCHEDULER_HEARTBEAT_KEY


@pytest.mark.asyncio
class TestReport:
    async def test_ok_with_fresh_heartbeat(
        self, session: AsyncSession, redis: Redis
    ) -> None:
        now = time.time()
        await redis.set(SCHEDULER_HEARTBEAT_KEY, str(now))
        report = await HealthService(session, redis).report(now=now)
        assert report["status"] == "ok"
        assert report["dependencies"] == {
            "postgres": "ok",
            "redis": "ok",
            "worker": "ok",
        }
        assert report["unhealthy_reasons"] == []

    async def test_stale_heartbeat_is_critical(
        self, session: AsyncSession, redis: Redis
    ) -> None:
        now = time.time()
        await redis.set(SCHEDULER_HEARTBEAT_KEY, str(now - 600))
        report = await HealthService(session, redis).report(now=now)
        assert report["status"] == "unhealthy"
        codes = {reason["code"] for reason in report["unhealthy_reasons"]}
        assert "worker_heartbeat_stale" in codes
        reason = report["unhealthy_reasons"][0]
        assert reason["severity"] == "critical"
        assert reason["remedy"]

    async def test_missing_heartbeat_within_grace_is_starting(
        self, session: AsyncSession, redis: Redis, mocker: MockerFixture
    ) -> None:
        now = time.time()
        mocker.patch.object(health_service, "STARTED_AT", now - 10)
        report = await HealthService(session, redis).report(now=now)
        assert report["dependencies"]["worker"] == "starting"
        assert report["status"] == "ok"

    async def test_lane_disabled_and_kill_switch(
        self, session: AsyncSession, redis: Redis, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        now = time.time()
        await redis.set(SCHEDULER_HEARTBEAT_KEY, str(now))
        monkeypatch.setattr(settings, "GEMINI_API_KEY", "k")
        await redis.set(DISABLED_KEY.format(provider="gemini"), "1")
        report = await HealthService(session, redis).report(now=now)
        assert {r["code"] for r in report["unhealthy_reasons"]} == {"llm_lane_disabled"}
        assert report["status"] == "unhealthy"

    async def test_chain_exhausted_warns_then_clears(
        self, session: AsyncSession, redis: Redis, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        now = time.time()
        await redis.set(SCHEDULER_HEARTBEAT_KEY, str(now))
        monkeypatch.setattr(settings, "GEMINI_API_KEY", "k")
        await redis.set("net:cooldown:gemini", "1", ex=60)
        report = await HealthService(session, redis).report(now=now)
        assert report["status"] == "degraded"
        assert report["unhealthy_reasons"][0]["code"] == "llm_chain_exhausted"
        await redis.delete("net:cooldown:gemini")
        report = await HealthService(session, redis).report(now=now + 1)
        assert report["unhealthy_reasons"][0]["detail"] == "clearing"
        await redis.delete("health:seen:llm_chain_exhausted")
        await redis.set(SCHEDULER_HEARTBEAT_KEY, str(now + 200))
        report = await HealthService(session, redis).report(now=now + 200)
        assert report["unhealthy_reasons"] == []

    async def test_engine_unreachable(
        self, session: AsyncSession, redis: Redis, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        now = time.time()
        await redis.set(SCHEDULER_HEARTBEAT_KEY, str(now))
        monkeypatch.setattr(settings, "ENGINE_URL", "http://127.0.0.1:9")
        monkeypatch.setattr(settings, "ENGINE_TIMEOUT_S", 0.2)
        report = await HealthService(session, redis).report(now=now)
        assert {r["code"] for r in report["unhealthy_reasons"]} == {
            "engine_unreachable"
        }
        assert report["status"] == "degraded"


@pytest.mark.asyncio
async def test_health_route(client: AsyncClient, redis: Redis) -> None:
    await redis.set(SCHEDULER_HEARTBEAT_KEY, str(time.time()))
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "runtime" in body
    assert "uptime_s" in body["runtime"]
    healthz = await client.get("/healthz")
    assert healthz.status_code == 200
