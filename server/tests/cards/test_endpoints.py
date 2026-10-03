import json
import time
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from pytest_mock import MockerFixture

from outception.cards import service as cards
from outception.net import state as signal_state
from outception.news import cache as news_cache
from outception.news import registry
from outception.news.clusters import service as clusters
from outception.news.schemas import NewsItem
from outception.postgres import AsyncSession
from outception.redis import Redis

_OPEN_METEO = {
    "timezone": "Europe/London",
    "current": {
        "temperature_2m": 14.2,
        "relative_humidity_2m": 70,
        "apparent_temperature": 13.0,
        "is_day": 1,
        "weather_code": 3,
        "wind_speed_10m": 12.0,
    },
    "daily": {
        "time": ["2026-10-04"],
        "weather_code": [3],
        "temperature_2m_max": [16.0],
        "temperature_2m_min": [9.0],
    },
}


def _item(url: str, title: str = "A headline") -> NewsItem:
    return NewsItem(id=url, title=title, url=url, pub_date=news_cache.now_ms())


@pytest.mark.asyncio
class TestFeedCards:
    async def test_feed_card_carries_state_and_cluster_fields(
        self,
        client: AsyncClient,
        redis: Redis,
        session: AsyncSession,
        mocker: MockerFixture,
    ) -> None:
        url = "https://example.com/story"
        await news_cache.set(redis, "bbc-world", [_item(url)])
        await clusters.Clusterer(session, redis).ingest("bbc-world", [_item(url)])
        await clusters.Clusterer(session, redis).ingest(
            "guardian", [_item(url + "?utm_source=x")]
        )
        response = await client.get("/v1/cards/bbc-world")
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["kind"] == "feed"
        assert body["state"] == "nominal"
        assert body["meta"]["id"] == "bbc-world"
        item = body["payload"]["items"][0]
        assert item["clusterId"]
        assert item["publisherCount"] == 2
        assert response.headers["Cache-Control"] == "private, no-store"
        # The legacy view of the same card carries none of the envelope fields.
        legacy = (await client.get("/v1/news/bbc-world")).json()
        assert "clusterId" not in legacy["items"][0]
        assert "state" not in legacy

    async def test_failure_record_degrades_then_falls_back(
        self, client: AsyncClient, redis: Redis
    ) -> None:
        await news_cache.set(redis, "bbc-world", [_item("https://example.com/a")])
        await signal_state.note_failure(redis, "bbc-world", "transient")
        assert (await client.get("/v1/cards/bbc-world")).json()["state"] == "degraded"
        key = signal_state.STATE_KEY.format(id="bbc-world")
        await redis.hset(key, "fail_since", str(time.time() - 2 * 86400))
        assert (await client.get("/v1/cards/bbc-world")).json()["state"] == "fallback"

    async def test_empty_for_a_day_is_fallback(
        self, client: AsyncClient, redis: Redis
    ) -> None:
        await news_cache.set(redis, "bbc-world", [_item("https://example.com/a")])
        await redis.set(
            cards.EMPTY_SINCE_KEY.format(id="bbc-world"),
            str(news_cache.now_ms() - 25 * 3600 * 1000),
        )
        assert (await client.get("/v1/cards/bbc-world")).json()["state"] == "fallback"

    async def test_unknown_and_disabled_are_404(self, client: AsyncClient) -> None:
        assert (await client.get("/v1/cards/no-such-card")).status_code == 404
        disabled = next(iter(registry.DISABLED_SOURCES & registry.SOURCES.keys()))
        assert (await client.get(f"/v1/cards/{disabled}")).status_code == 404


@pytest.mark.asyncio
class TestOtherKinds:
    async def test_table_card(self, client: AsyncClient, mocker: MockerFixture) -> None:
        mocker.patch(
            "outception.news.heatmap.providers.http.fetch_json",
            AsyncMock(
                return_value=[
                    {
                        "symbol": "btc",
                        "name": "Bitcoin",
                        "current_price": 1.0,
                        "market_cap": 10,
                        "price_change_percentage_24h": 1.0,
                    }
                ]
            ),
        )
        response = await client.get("/v1/cards/heatmap-crypto")
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["kind"] == "table"
        assert body["state"] == "nominal"
        assert body["payload"]["tiles"][0]["symbol"] == "BTC"
        assert body["payload"]["tiles"][0]["subtitle"] is None
        assert response.headers["Cache-Control"].startswith("public, max-age=60")

    async def test_briefing_card(self, client: AsyncClient, redis: Redis) -> None:
        assert (await client.get("/v1/cards/briefing:developer")).status_code == 404
        assert (await client.get("/v1/cards/briefing:nope")).status_code == 404
        from outception.news.briefing.builder import LATEST_KEY, STALE_AFTER_MS

        now = news_cache.now_ms()
        await redis.set(
            LATEST_KEY.format(profile="developer"),
            json.dumps(
                {
                    "profile": "developer",
                    "builtAt": now,
                    "staleAfterMs": STALE_AFTER_MS,
                    "items": [],
                }
            ),
        )
        response = await client.get("/v1/cards/briefing:developer")
        assert response.status_code == 200
        body = response.json()
        assert body["kind"] == "briefing"
        assert body["meta"] is None
        assert body["payload"]["profile"] == "developer"
        assert body["updatedAt"] == now

    async def test_weather_strip_for_country_and_city(
        self, client: AsyncClient, mocker: MockerFixture
    ) -> None:
        fetch = mocker.patch(
            "outception.news.weather._fetch", AsyncMock(return_value=_OPEN_METEO)
        )
        response = await client.get(
            "/v1/cards/weather", params={"attachedTo": "gnews-jp"}
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["kind"] == "strip"
        assert body["payload"]["attachedTo"] == "gnews-jp"
        assert body["payload"]["weather"]["location"] == "Tokyo"
        assert fetch.await_args is not None
        assert fetch.await_args.args == (35.6762, 139.6503)
        response = await client.get(
            "/v1/cards/weather",
            params={"attachedTo": "city-unitedstates-newyork", "country": "US"},
        )
        assert response.status_code == 200
        assert fetch.await_args is not None
        assert fetch.await_args.args == (40.71, -74.01)
        assert response.headers["Vary"] == "Origin, CF-IPCountry"


@pytest.mark.asyncio
class TestStory:
    async def test_story_lists_every_publisher(
        self, client: AsyncClient, redis: Redis, session: AsyncSession
    ) -> None:
        clusterer = clusters.Clusterer(session, redis)
        await clusterer.ingest(
            "bbc-world", [_item("https://example.com/s", "Council backs plan")]
        )
        await clusterer.ingest(
            "guardian", [_item("https://example.com/s?ref=x", "Council backs plan")]
        )
        await session.commit()
        found = await clusters.cluster_for_urls(redis, ["https://example.com/s"])
        cluster_id = found["https://example.com/s"][0]
        response = await client.get(f"/v1/news/story/{cluster_id}")
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["publisherCount"] == 2
        assert body["leadSourceName"] == "BBC News"
        assert [m["sourceId"] for m in body["items"]] == ["bbc-world", "guardian"]
        assert (await client.get("/v1/news/story/not-a-uuid")).status_code == 404
        assert (
            await client.get("/v1/news/story/00000000-0000-0000-0000-000000000000")
        ).status_code == 404
