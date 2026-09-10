import pytest
from httpx import AsyncClient

from outception.promoted import service
from outception.promoted.schemas import QueuedPromotion
from outception.redis import Redis


def _queued(**overrides: object) -> QueuedPromotion:
    defaults: dict[str, object] = {
        "id": "run1",
        "businessName": "Corner Cafe",
        "videoUrl": "https://cdn.example.com/ad.mp4",
        "clickUrl": "https://cornercafe.example",
        "tagline": "Fresh pastries daily",
        "durationSeconds": 3600,
    }
    defaults.update(overrides)
    return QueuedPromotion.model_validate(defaults)


@pytest.mark.asyncio
class TestActiveSlot:
    async def test_no_slot_returns_null(self, client: AsyncClient) -> None:
        response = await client.get("/v1/promoted/active")
        assert response.status_code == 200
        assert response.json() is None
        assert "max-age" in response.headers["cache-control"]

    async def test_queued_run_activates_on_first_read(
        self, client: AsyncClient, redis: Redis
    ) -> None:
        await service.enqueue(redis, _queued())
        response = await client.get("/v1/promoted/active")
        body = response.json()
        assert body["id"] == "run1"
        assert body["businessName"] == "Corner Cafe"
        assert body["videoUrl"] == "https://cdn.example.com/ad.mp4"
        assert body["endsAt"]
        # The queue advanced: the entry now lives in the active key.
        assert await service.list_queue(redis) == []
        assert await redis.ttl(service.ACTIVE_KEY) == 3600

    async def test_fifo_order_and_stop(self, client: AsyncClient, redis: Redis) -> None:
        await service.enqueue(redis, _queued(id="first"))
        await service.enqueue(redis, _queued(id="second"))
        first = await client.get("/v1/promoted/active")
        assert first.json()["id"] == "first"
        # Stopping the active run advances to the next queued one.
        assert await service.stop_active(redis)
        second = await client.get("/v1/promoted/active")
        assert second.json()["id"] == "second"

    async def test_non_http_urls_are_neutralized(
        self, client: AsyncClient, redis: Redis
    ) -> None:
        await service.enqueue(
            redis,
            _queued(videoUrl="javascript:alert(1)", clickUrl="data:text/html,x"),
        )
        response = await client.get("/v1/promoted/active")
        body = response.json()
        assert body["videoUrl"] == ""
        # clickUrl neutralizes to "" and exclude_none keeps empty strings.
        assert body.get("clickUrl", "") == ""


@pytest.mark.asyncio
class TestDeadLetter:
    async def test_malformed_queue_entry_is_skipped(
        self, client: AsyncClient, redis: Redis
    ) -> None:
        await redis.rpush(service.QUEUE_KEY, "{not json")
        await service.enqueue(redis, _queued(id="good"))
        response = await client.get("/v1/promoted/active")
        assert response.json()["id"] == "good"
        assert await redis.llen(service.DEAD_KEY) == 1
