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

    async def test_ids_subset(self, client: AsyncClient) -> None:
        response = await client.get(
            "/v1/news/sources",
            params={"ids": "hackernews,not-a-real-source,hackernews"},
        )
        assert response.status_code == 200
        assert [s["id"] for s in response.json()] == ["hackernews"]
        assert "s-maxage" in response.headers["cache-control"]

    async def test_single_source_metadata(self, client: AsyncClient) -> None:
        response = await client.get("/v1/news/sources/hackernews")
        assert response.status_code == 200
        assert response.json()["id"] == "hackernews"
        assert "s-maxage" in response.headers["cache-control"]
        missing = await client.get("/v1/news/sources/not-a-real-source")
        assert missing.status_code == 404


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

    async def test_serves_cached_translations_without_calling_a_model(
        self, client: AsyncClient, redis: Redis, mocker: MockerFixture
    ) -> None:
        """The wall's first paint used to be English whatever the reader's
        language. Batch must translate from cache only: a maxed request covers
        256 sources, so translating on demand here would be a burst of
        thousands of headlines."""
        from outception.news import cache as news_cache
        from outception.news import translate

        await news_cache.set(
            redis,
            "hackernews",
            [
                NewsItem(id="1", title="Hello world", url="https://example.com/1"),
                NewsItem(id="2", title="Second story", url="https://example.com/2"),
            ],
        )
        # Only the first headline is already translated.
        await redis.set(translate._cache_key("de", "Hello world"), "Hallo Welt")
        generate = mocker.patch.object(translate, "_generate", AsyncMock())

        response = await client.post(
            "/v1/news/batch", json={"sources": ["hackernews"], "lang": "de"}
        )
        assert response.status_code == 200
        (card,) = response.json()
        assert [i["title"] for i in card["items"]] == ["Hallo Welt", "Second story"]
        # The untranslated one is flagged so the client keeps polling.
        assert card["translationsPending"] is True
        generate.assert_not_awaited()

    async def test_no_lang_is_unchanged_and_not_pending(
        self, client: AsyncClient, redis: Redis
    ) -> None:
        from outception.news import cache as news_cache

        await news_cache.set(
            redis,
            "hackernews",
            [NewsItem(id="1", title="Hello world", url="https://example.com/1")],
        )
        response = await client.post("/v1/news/batch", json={"sources": ["hackernews"]})
        (card,) = response.json()
        assert card["items"][0]["title"] == "Hello world"
        assert card["translationsPending"] is False

    async def test_identity_translation_is_not_pending(
        self, client: AsyncClient, redis: Redis
    ) -> None:
        """A brand name translates to itself. Pending used to be inferred from
        "the title came back unchanged", so a fully warm card reported pending
        for good and the wall re-polled work that was already done."""
        from outception.news import cache as news_cache
        from outception.news import translate

        await news_cache.set(
            redis,
            "hackernews",
            [NewsItem(id="1", title="iPhone Duo", url="https://example.com/1")],
        )
        # Cached, and the correct Japanese rendering is the original.
        await redis.set(translate._cache_key("ja", "iPhone Duo"), "iPhone Duo")
        response = await client.post(
            "/v1/news/batch", json={"sources": ["hackernews"], "lang": "ja"}
        )
        (card,) = response.json()
        assert card["items"][0]["title"] == "iPhone Duo"
        assert card["translationsPending"] is False

    async def test_pending_is_per_source_not_whole_batch(
        self, client: AsyncClient, redis: Redis
    ) -> None:
        """One cold source must not mark every other card in the batch pending."""
        from outception.news import cache as news_cache
        from outception.news import translate

        await news_cache.set(
            redis,
            "hackernews",
            [NewsItem(id="1", title="Hello world", url="https://example.com/1")],
        )
        await news_cache.set(
            redis,
            "producthunt",
            [NewsItem(id="2", title="Second story", url="https://example.com/2")],
        )
        # Only the first source's headline is translated.
        await redis.set(translate._cache_key("de", "Hello world"), "Hallo Welt")

        response = await client.post(
            "/v1/news/batch",
            json={"sources": ["hackernews", "producthunt"], "lang": "de"},
        )
        by_id = {c["id"]: c for c in response.json()}
        assert by_id["hackernews"]["translationsPending"] is False
        assert by_id["producthunt"]["translationsPending"] is True

    async def test_fully_translated_card_is_not_pending(
        self, client: AsyncClient, redis: Redis
    ) -> None:
        from outception.news import cache as news_cache
        from outception.news import translate

        await news_cache.set(
            redis,
            "hackernews",
            [NewsItem(id="1", title="Hello world", url="https://example.com/1")],
        )
        await redis.set(translate._cache_key("de", "Hello world"), "Hallo Welt")
        response = await client.post(
            "/v1/news/batch", json={"sources": ["hackernews"], "lang": "de"}
        )
        (card,) = response.json()
        assert card["items"][0]["title"] == "Hallo Welt"
        assert card["translationsPending"] is False


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

    async def test_untranslated_hit_is_flagged_pending(
        self, client: AsyncClient, redis: Redis, mocker: MockerFixture
    ) -> None:
        """Search is cache-first and never waits on a model, so the first
        search in a language can only answer in the original text. Without this
        flag the client had no way to know to ask again, and the results stayed
        English until the reader retyped the query."""
        from outception.config import settings
        from outception.news import cache, translate

        await cache.set(
            redis,
            "hackernews",
            [NewsItem(id="1", title="Rust 2.0 released today", url="https://e.com")],
        )
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", "k")
        # Keep the test off the network: the miss would otherwise translate in
        # the background.
        mocker.patch.object(translate, "_generate", AsyncMock())

        response = await client.get(
            "/v1/news/search", params={"q": "rust", "lang": "de"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["items"][0]["item"]["title"] == "Rust 2.0 released today"
        assert body["translationsPending"] is True

    async def test_translated_hit_is_not_pending(
        self, client: AsyncClient, redis: Redis, mocker: MockerFixture
    ) -> None:
        from outception.config import settings
        from outception.news import cache, translate

        title = "Rust 2.0 released today"
        await cache.set(
            redis, "hackernews", [NewsItem(id="1", title=title, url="https://e.com")]
        )
        await redis.set(translate._cache_key("de", title), "Rust 2.0 heute erschienen")
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", "k")

        response = await client.get(
            "/v1/news/search", params={"q": "rust", "lang": "de"}
        )
        body = response.json()
        assert body["items"][0]["item"]["title"] == "Rust 2.0 heute erschienen"
        assert body["translationsPending"] is False


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
    async def test_follow_heatmap_card(self, client: AsyncClient) -> None:
        # Heatmap cards have no getter but sit in the card set like any source.
        assert (await client.put("/v1/news/followed/heatmap-crypto")).status_code == 204
        followed = (await client.get("/v1/news/followed")).json()["sourceIds"]
        assert "heatmap-crypto" in followed
        assert (
            await client.delete("/v1/news/followed/heatmap-crypto")
        ).status_code == 204

    @pytest.mark.auth
    async def test_follow_resolves_redirect_alias(self, client: AsyncClient) -> None:
        # `github` is a redirect alias for `github-trending-today`.
        assert (await client.put("/v1/news/followed/github")).status_code == 204
        followed = (await client.get("/v1/news/followed")).json()["sourceIds"]
        assert "github-trending-today" in followed


@pytest.mark.asyncio
class TestTranslateAhead:
    async def test_fresh_fetch_translates_for_other_readers(
        self, client: AsyncClient, redis: Redis, mocker: MockerFixture
    ) -> None:
        """A request that refreshes a feed kicks off translation into the
        languages this source's other readers use - not the requester's own
        (that one is translated inline) - and records its own language as
        demand for next time."""
        from outception.news import translate

        getter = AsyncMock(
            return_value=[NewsItem(id="1", title="Hello", url="https://example.com")]
        )
        mocker.patch.dict("outception.news.registry.GETTERS", {"hackernews": getter})
        for _ in range(2):
            await translate.note_source_language_demand(redis, "hackernews", "hr")
        ahead = mocker.patch.object(
            translate, "translate_texts", AsyncMock(return_value=["Bok"])
        )
        response = await client.get(
            "/v1/news/hackernews", params={"lang": "de", "latest": "true"}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        await translate.drain_translate_ahead(timeout=5)
        ahead.assert_awaited_once_with(redis, ["Hello"], "hr", budget="warmer")
        # The requester's language counts towards next time (one hit so far).
        await client.get("/v1/news/hackernews", params={"lang": "de"})
        assert await translate.source_demanded_targets(redis, "hackernews") == [
            "de",
            "hr",
        ]

    async def test_cache_hit_does_not_translate_ahead(
        self, client: AsyncClient, redis: Redis, mocker: MockerFixture
    ) -> None:
        from outception.news import cache as news_cache
        from outception.news import translate

        await news_cache.set(
            redis,
            "hackernews",
            [NewsItem(id="1", title="Hello", url="https://example.com")],
        )
        for _ in range(2):
            await translate.note_source_language_demand(redis, "hackernews", "hr")
        ahead = mocker.patch.object(translate, "translate_texts", AsyncMock())
        response = await client.get("/v1/news/hackernews", params={"lang": "de"})
        # A fresh-enough entry also reports "success"; what matters is that no
        # fetch happened, so nothing is translated ahead on a plain poll.
        assert response.status_code == 200
        await translate.drain_translate_ahead(timeout=5)
        ahead.assert_not_awaited()


@pytest.mark.asyncio
class TestGetSummary:
    _URL = "https://example.com/story-of-the-day"

    async def test_finished_result_is_edge_cacheable(
        self, client: AsyncClient, mocker: MockerFixture
    ) -> None:
        from outception.news.summary import SummaryResult

        mocker.patch(
            "outception.news.endpoints._summarizable", AsyncMock(return_value=True)
        )
        mocker.patch(
            "outception.news.summary.get_summary_result",
            AsyncMock(return_value=SummaryResult("Zusammenfassung.", "summary")),
        )
        response = await client.get(
            "/v1/news/summary", params={"url": self._URL, "lang": "de"}
        )
        assert response.status_code == 200
        assert "s-maxage" in response.headers["cache-control"]
        body = response.json()
        assert body["summary"] == "Zusammenfassung."
        assert body["translationsPending"] is False

    async def test_untranslated_teaser_is_never_cached(
        self, client: AsyncClient, mocker: MockerFixture
    ) -> None:
        """The publisher's original-language line must not sit at the edge for
        a day under the reader's language: no-store, and flagged so the app
        polls for the translated line."""
        from outception.news.summary import SummaryResult

        mocker.patch(
            "outception.news.endpoints._summarizable", AsyncMock(return_value=True)
        )
        mocker.patch(
            "outception.news.summary.get_summary_result",
            AsyncMock(
                return_value=SummaryResult(
                    "The publisher standfirst.", "teaser", translation_pending=True
                )
            ),
        )
        response = await client.get(
            "/v1/news/summary", params={"url": self._URL, "lang": "de"}
        )
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        body = response.json()
        assert body["kind"] == "teaser"
        assert body["translationsPending"] is True
