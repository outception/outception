from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from pytest_mock import MockerFixture

from outception.news.schemas import NewsItem
from outception.redis import Redis


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

    async def test_cold_cache_serves_from_getter(
        self, client: AsyncClient, mocker: MockerFixture
    ) -> None:
        # Empty cache (fakeredis) → the endpoint calls the registered getter.
        # Mock it so no outbound fetch happens.
        getter = AsyncMock(
            return_value=[NewsItem(id="1", title="Hello", url="https://example.com")]
        )
        mocker.patch.dict("outception.news.registry.GETTERS", {"hackernews": getter})

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


@pytest.mark.asyncio
class TestSearch:
    async def test_short_query_rejected(self, client: AsyncClient) -> None:
        response = await client.get("/v1/news/search", params={"q": "a"})
        assert response.status_code == 422

    async def test_matches_source_by_name(self, client: AsyncClient) -> None:
        response = await client.get("/v1/news/search", params={"q": "hacker"})
        assert response.status_code == 200
        body = response.json()
        assert any(s["id"] == "hackernews" for s in body["sources"])

    async def test_matches_cached_headline(
        self, client: AsyncClient, redis: Redis
    ) -> None:
        from outception.news import cache

        await cache.set(
            redis,
            "hackernews",
            [NewsItem(id="1", title="Rust 2.0 released today", url="https://e.com")],
        )
        response = await client.get("/v1/news/search", params={"q": "rust"})
        assert response.status_code == 200
        items = response.json()["items"]
        assert len(items) == 1
        assert items[0]["sourceId"] == "hackernews"
        assert "Rust" in items[0]["item"]["title"]

    async def test_no_headline_match_on_cold_cache(self, client: AsyncClient) -> None:
        response = await client.get("/v1/news/search", params={"q": "zxqwv"})
        assert response.status_code == 200
        assert response.json()["items"] == []


@pytest.mark.asyncio
class TestFollow:
    async def test_list_anonymous(self, client: AsyncClient) -> None:
        assert (await client.get("/v1/news/followed")).status_code == 401

    @pytest.mark.auth
    async def test_follow_list_unfollow(self, client: AsyncClient) -> None:
        assert (await client.get("/v1/news/followed")).json()["sourceIds"] == []

        assert (await client.put("/v1/news/followed/hackernews")).status_code == 204
        # idempotent
        assert (await client.put("/v1/news/followed/hackernews")).status_code == 204
        followed = (await client.get("/v1/news/followed")).json()["sourceIds"]
        assert followed.count("hackernews") == 1

        assert (await client.delete("/v1/news/followed/hackernews")).status_code == 204
        assert (
            "hackernews"
            not in (await client.get("/v1/news/followed")).json()["sourceIds"]
        )

    @pytest.mark.auth
    async def test_follow_unknown_source_404(self, client: AsyncClient) -> None:
        response = await client.put("/v1/news/followed/not-a-real-source")
        assert response.status_code == 404

    async def test_feed_anonymous(self, client: AsyncClient) -> None:
        assert (await client.get("/v1/news/followed/feed")).status_code == 401

    @pytest.mark.auth
    async def test_feed_merges_warm_cache_freshest_first(
        self, client: AsyncClient, redis: Redis
    ) -> None:
        from outception.news import cache

        await cache.set(
            redis,
            "hackernews",
            [
                NewsItem(id="1", title="Older", url="https://e.com/1", pub_date=1000),
                NewsItem(id="2", title="Newer", url="https://e.com/2", pub_date=2000),
            ],
        )
        await client.put("/v1/news/followed/hackernews")

        response = await client.get("/v1/news/followed/feed")
        assert response.status_code == 200
        items = response.json()["items"]
        assert [i["item"]["title"] for i in items] == ["Newer", "Older"]
        assert all(i["sourceId"] == "hackernews" for i in items)

    @pytest.mark.auth
    async def test_follow_resolves_redirect_alias(self, client: AsyncClient) -> None:
        # `github` is a redirect alias for `github-trending-today`.
        assert (await client.put("/v1/news/followed/github")).status_code == 204
        followed = (await client.get("/v1/news/followed")).json()["sourceIds"]
        assert "github-trending-today" in followed
