from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from pytest_mock import MockerFixture

from polar.news.schemas import NewsItem


@pytest.mark.asyncio
class TestListSources:
    async def test_returns_source_metadata(self, client: AsyncClient) -> None:
        response = await client.get("/v1/news/sources")
        assert response.status_code == 200
        body = response.json()
        assert len(body) > 100
        ids = {s["id"] for s in body}
        assert "hackernews" in ids
        sample = next(s for s in body if s["id"] == "hackernews")
        assert sample["interval"] > 0
        assert sample["name"]


@pytest.mark.asyncio
class TestGetSource:
    async def test_unknown_source_returns_404(self, client: AsyncClient) -> None:
        response = await client.get("/v1/news/not-a-real-source")
        assert response.status_code == 404

    async def test_invalid_sort_returns_422(self, client: AsyncClient) -> None:
        response = await client.get("/v1/news/hackernews", params={"sort": "nonsense"})
        assert response.status_code == 422

    async def test_cold_cache_serves_from_getter(
        self, client: AsyncClient, mocker: MockerFixture
    ) -> None:
        # Empty cache (fakeredis) → the endpoint calls the registered getter.
        # Mock it so no outbound fetch happens.
        getter = AsyncMock(
            return_value=[NewsItem(id="1", title="Hello", url="https://example.com")]
        )
        mocker.patch.dict("polar.news.registry.GETTERS", {"hackernews": getter})

        response = await client.get("/v1/news/hackernews")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "success"
        assert body["id"] == "hackernews"
        assert body["items"][0]["title"] == "Hello"
        getter.assert_awaited_once()


@pytest.mark.asyncio
class TestBatch:
    async def test_empty_sources_rejected(self, client: AsyncClient) -> None:
        response = await client.post("/v1/news/batch", json={"sources": []})
        assert response.status_code == 422

    async def test_cold_and_unknown_sources_absent(self, client: AsyncClient) -> None:
        # Batch never triggers fetches: with an empty cache, cold and unknown
        # sources are simply absent from the response.
        response = await client.post(
            "/v1/news/batch",
            json={"sources": ["hackernews", "not-a-real-source"]},
        )
        assert response.status_code == 200
        assert response.json() == []
