"""The fast paths added for performance must produce identical results to the
plain ones - a splice or a gate that drops a headline is a wrong answer, not a
slow one."""

import pytest

from outception.news import cache, search
from outception.news.schemas import NewsItem
from outception.redis import Redis


@pytest.mark.asyncio
class TestTitlesGate:
    async def test_finds_the_same_headlines_as_a_full_scan(self, redis: Redis) -> None:
        await cache.set(
            redis,
            "hackernews",
            [
                NewsItem(
                    id="1", title="Rust 2.0 released today", url="https://e.com/1"
                ),
                NewsItem(id="2", title="Climate talks resume", url="https://e.com/2"),
            ],
        )
        hits = await search.search_headlines(redis, "rust")
        assert [h.item.id for h in hits] == ["1"]
        assert await search.search_headlines(redis, "climate")
        assert await search.search_headlines(redis, "zxqwv") == []

    async def test_matches_a_title_not_a_url(self, redis: Redis) -> None:
        """The gate gets titles only, so a query that appears in a URL but in
        no headline must not produce a hit."""
        await cache.set(
            redis,
            "hackernews",
            [NewsItem(id="1", title="A quiet morning", url="https://zebra.example/x")],
        )
        assert await search.search_headlines(redis, "zebra") == []

    async def test_falls_back_when_a_source_has_no_titles_blob(
        self, redis: Redis
    ) -> None:
        """Entries written before the blob existed must still be searchable,
        or search would go blind on them until they were refetched."""
        await cache.set(
            redis,
            "hackernews",
            [NewsItem(id="1", title="Rust 2.0 released today", url="https://e.com/1")],
        )
        await redis.delete(cache.titles_key("hackernews"))
        hits = await search.search_headlines(redis, "rust")
        assert [h.item.id for h in hits] == ["1"]
