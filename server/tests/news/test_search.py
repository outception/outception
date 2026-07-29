import pytest

from outception.news import cache, search
from outception.news.cache import now_ms
from outception.news.schemas import NewsItem
from outception.redis import Redis


def _item(title: str, story_id: str = "story") -> NewsItem:
    return NewsItem(
        id=story_id,
        title=title,
        url="https://example.com/a",
        pub_date=now_ms(),
    )


def _a_searchable_source() -> str:
    return search._SEARCHABLE_SOURCE_IDS[0]


@pytest.mark.asyncio
class TestSearchHeadlines:
    async def test_finds_a_headline_by_substring(self, redis: Redis) -> None:
        source_id = _a_searchable_source()
        await cache.set(redis, source_id, [_item("Something about Tornadoes today")])

        hits = await search.search_headlines(redis, "tornado")

        assert [h.item.title for h in hits] == ["Something about Tornadoes today"]

    async def test_ignores_a_match_outside_the_title(self, redis: Redis) -> None:
        # The raw probe passes (the word IS in the payload's url), but only
        # titles are searchable — the title gate has to reject it.
        source_id = _a_searchable_source()
        item = NewsItem(
            id="story",
            title="An ordinary headline",
            url="https://example.com/tornado-warning",
            pub_date=now_ms(),
        )
        await cache.set(redis, source_id, [item])

        assert await search.search_headlines(redis, "tornado") == []

    async def test_matches_case_insensitively(self, redis: Redis) -> None:
        source_id = _a_searchable_source()
        await cache.set(redis, source_id, [_item("TORNADO Warning Issued")])

        hits = await search.search_headlines(redis, "tornado")

        assert len(hits) == 1

    async def test_matches_a_capitalised_non_ascii_query(self, redis: Redis) -> None:
        """The fast path probes raw BYTES, where `IGNORECASE` folds ASCII only.
        A Cyrillic query against a capitalised Cyrillic headline must still
        match — that is the case a bytes-only probe would silently drop."""
        source_id = _a_searchable_source()
        await cache.set(redis, source_id, [_item("Президент выступил сегодня")])

        hits = await search.search_headlines(redis, "президент")

        assert len(hits) == 1

    async def test_query_with_regex_metacharacters_is_literal(
        self, redis: Redis
    ) -> None:
        source_id = _a_searchable_source()
        await cache.set(redis, source_id, [_item("Profits up 12% (again)")])

        assert len(await search.search_headlines(redis, "12% (again)")) == 1
        # A metacharacter-laden query that does NOT occur must not blow up or
        # match everything by being compiled as a pattern.
        assert await search.search_headlines(redis, ".*") == []

    async def test_respects_the_limit(self, redis: Redis) -> None:
        source_id = _a_searchable_source()
        await cache.set(
            redis,
            source_id,
            [_item(f"Tornado number {i}", story_id=f"s{i}") for i in range(5)],
        )

        assert len(await search.search_headlines(redis, "tornado", limit=2)) == 2

    async def test_cold_sources_are_simply_absent(self, redis: Redis) -> None:
        assert await search.search_headlines(redis, "tornado") == []


@pytest.mark.asyncio
class TestWarmSourceIndex:
    """The index that keeps search from MGETing the whole ~10,000 source
    roster. It is a hint: wrong in either direction it must not change what a
    search returns, only how much work finding it costs."""

    async def test_a_write_registers_the_source(self, redis: Redis) -> None:
        source_id = _a_searchable_source()
        await cache.set(redis, source_id, [_item("Tornado watch")])

        members = {
            m.decode() if isinstance(m, bytes) else m
            for m in await redis.smembers(cache.WARM_SOURCES_KEY)
        }
        assert source_id in members

    async def test_finds_headlines_when_the_index_is_cold(self, redis: Redis) -> None:
        """Entries written before the index existed are still found — the
        first search falls back to the full roster and backfills."""
        source_id = _a_searchable_source()
        await cache.set(redis, source_id, [_item("Tornado watch")])
        await redis.delete(cache.WARM_SOURCES_KEY)

        assert len(await search.search_headlines(redis, "tornado")) == 1
        members = {
            m.decode() if isinstance(m, bytes) else m
            for m in await redis.smembers(cache.WARM_SOURCES_KEY)
        }
        assert source_id in members, "the fallback scan should backfill"

    async def test_prunes_sources_whose_entry_expired(self, redis: Redis) -> None:
        source_id = _a_searchable_source()
        await cache.set(redis, source_id, [_item("Tornado watch")])
        # The entry ages out but the set has no per-member TTL, so the id is
        # left behind — the next search should drop it.
        await redis.delete(cache.cache_key(source_id))

        assert await search.search_headlines(redis, "tornado") == []
        assert await redis.smembers(cache.WARM_SOURCES_KEY) == set()

    async def test_a_stale_extra_member_cannot_break_a_search(
        self, redis: Redis
    ) -> None:
        source_id = _a_searchable_source()
        await cache.set(redis, source_id, [_item("Tornado watch")])
        await redis.sadd(cache.WARM_SOURCES_KEY, "a-source-that-never-existed")

        assert len(await search.search_headlines(redis, "tornado")) == 1
