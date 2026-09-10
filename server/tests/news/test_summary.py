import asyncio
from unittest.mock import AsyncMock

import httpx
import pytest
from bs4 import BeautifulSoup
from pytest_mock import MockerFixture

from outception.config import settings
from outception.exceptions import OutceptionError
from outception.news import cache as news_cache
from outception.news import summary
from outception.news.fetch import NewsFetchError, UnsafeURLError
from outception.redis import Redis


async def _counter(redis: Redis, key: str) -> int:
    """The Redis client is typed ``str | None``; a counter these tests
    assert on is written by the code under test, so absent means zero."""
    return int(await redis.get(key) or 0)


async def _know(redis: Redis, *urls: str) -> None:
    """Mark *urls* as headlines the wall has served - is_available answers
    False for anything outside that allowlist."""
    for url in urls:
        await redis.set(news_cache.known_key(url), "1")


def _today() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).strftime("%Y%m%d")


_URL = "https://example.com/story"
_HTML = "<html><body><article>{}</article></body></html>".format(
    "".join(f"<p>{'word ' * 30}sentence {i}.</p>" for i in range(12))
)


def _soup() -> BeautifulSoup:
    return BeautifulSoup(_HTML, "lxml")


class TestExtractArticleText:
    def test_prefers_article_paragraphs(self) -> None:
        text = summary.extract_article_text(_soup())
        assert "sentence 0." in text
        assert len(text) > summary._MIN_ARTICLE_CHARS

    def test_unsummarizable_hosts(self) -> None:
        assert not summary._is_unsummarizable(
            "https://news.google.com/rss/articles/x?oc=5"
        )
        assert summary._is_unsummarizable("https://www.youtube.com/watch?v=x")
        assert summary._is_unsummarizable("https://[bad")
        assert not summary._is_unsummarizable(_URL)

    def test_strips_chrome(self) -> None:
        soup = BeautifulSoup(
            "<html><body><nav><p>menu menu menu</p></nav>"
            "<article><p>" + "content " * 60 + "</p></article></body></html>",
            "lxml",
        )
        text = summary.extract_article_text(soup)
        assert "menu" not in text


@pytest.mark.asyncio
class TestGetSummary:
    async def test_not_configured(self, redis: Redis, mocker: MockerFixture) -> None:
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", None)
        mocker.patch.object(settings, "GEMINI_API_KEY", None)
        with pytest.raises(OutceptionError) as exc_info:
            await summary.get_summary(redis, _URL, "en")
        assert exc_info.value.status_code == 503

    async def test_gemini_only_is_configured(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", None)
        mocker.patch.object(settings, "GEMINI_API_KEY", "g")
        mocker.patch("outception.news.summary.fetch_html", return_value=_soup())
        mocker.patch("outception.news.summary._summarize", return_value="gist")
        assert await summary.get_summary(redis, _URL, "en") == "gist"

    async def test_cache_hit_skips_model(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", "k")
        fetch_mock = mocker.patch("outception.news.summary.fetch_html")
        await redis.set(
            summary._CACHE_KEY.format(digest=summary._digest(_URL, "en")), "cached!"
        )
        assert await summary.get_summary(redis, _URL, "en") == "cached!"
        fetch_mock.assert_not_called()

    async def test_generates_and_caches(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", "k")
        mocker.patch("outception.news.summary.fetch_html", return_value=_soup())
        mocker.patch("outception.news.summary._summarize", return_value="the gist")

        assert await summary.get_summary(redis, _URL, "en") == "the gist"
        cached = await redis.get(
            summary._CACHE_KEY.format(digest=summary._digest(_URL, "en"))
        )
        assert cached in ("the gist", b"the gist")

    async def test_concurrent_taps_share_one_generation(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", "k")
        mocker.patch("outception.news.summary.fetch_html", return_value=_soup())

        async def slow_summarize(*args: object) -> str:
            await asyncio.sleep(0.05)
            return "the gist"

        summarize = mocker.patch(
            "outception.news.summary._summarize", side_effect=slow_summarize
        )
        results = await asyncio.gather(
            *(summary.get_summary(redis, _URL, "en") for _ in range(3))
        )
        assert results == ["the gist"] * 3
        assert summarize.call_count == 1
        assert (
            await redis.get(
                summary._PENDING_KEY.format(digest=summary._digest(_URL, "en"))
            )
            is None
        )

    async def test_waiter_gives_up_when_producer_fails(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", "k")
        mocker.patch.object(summary, "_PENDING_WAIT_SECONDS", 1.0)
        fetch_mock = mocker.patch("outception.news.summary.fetch_html")
        digest = summary._digest(_URL, "en")
        await redis.set(summary._PENDING_KEY.format(digest=digest), "1", ex=1)
        with pytest.raises(OutceptionError) as exc_info:
            await summary.get_summary(redis, _URL, "en")
        assert exc_info.value.status_code == 502
        fetch_mock.assert_not_called()

    async def test_fetch_failure_sets_marker(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", "k")
        fetch_mock = mocker.patch(
            "outception.news.summary.fetch_html",
            side_effect=NewsFetchError("blocked"),
        )
        mocker.patch(
            "outception.news.summary._reader_text",
            side_effect=NewsFetchError("reader blocked"),
        )
        # The new contract: a failed fetch may still yield the publisher's
        # teaser instead of an error - either way the fail marker must be set
        # and the fetch never retried on the next tap.
        try:
            await summary.get_summary(redis, _URL, "en")
        except OutceptionError:
            pass
        assert (
            await redis.get(
                summary._FAIL_KEY.format(digest=summary._digest(_URL, "en"))
            )
            is not None
        )
        try:
            await summary.get_summary(redis, _URL, "en")
        except OutceptionError:
            pass
        assert fetch_mock.call_count == 1

    async def test_daily_cap(self, redis: Redis, mocker: MockerFixture) -> None:
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", "k")
        mocker.patch.object(settings, "SUMMARY_DAILY_CAP", 0)
        fetch_mock = mocker.patch("outception.news.summary.fetch_html")
        with pytest.raises(OutceptionError) as exc_info:
            await summary.get_summary(redis, _URL, "en")
        assert exc_info.value.status_code == 502
        fetch_mock.assert_not_called()

    async def test_unreachable_article_costs_no_budget(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", "k")
        mocker.patch(
            "outception.news.summary.fetch_html",
            side_effect=NewsFetchError("HTTP 403"),
        )
        mocker.patch.object(settings, "READER_FALLBACK_ENABLED", False)
        with pytest.raises(OutceptionError):
            await summary.get_summary(redis, _URL, "en")
        assert await redis.get(summary._DAILY_KEY.format(day=_today())) is None

    async def test_reaching_the_model_costs_one(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", "k")
        mocker.patch("outception.news.summary.fetch_html", return_value=_soup())
        mocker.patch("outception.news.summary._summarize", return_value="A summary.")
        await summary.get_summary(redis, _URL, "en")
        used = await redis.get(summary._DAILY_KEY.format(day=_today()))
        assert used is not None
        assert int(used) == 1

    async def test_no_article_sentinel_not_cached(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", "k")
        mocker.patch("outception.news.summary.fetch_html", return_value=_soup())
        mocker.patch("outception.news.summary._summarize", return_value="NO_ARTICLE")
        with pytest.raises(OutceptionError) as exc_info:
            await summary.get_summary(redis, _URL, "en")
        assert exc_info.value.status_code == 502
        cached = await redis.get(
            summary._CACHE_KEY.format(digest=summary._digest(_URL, "en"))
        )
        assert cached is None

    async def test_unsummarizable_host_skips_fetch_and_budget(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", "k")
        fetch_mock = mocker.patch("outception.news.summary.fetch_html")
        with pytest.raises(OutceptionError) as exc_info:
            await summary.get_summary(
                redis, "https://www.youtube.com/watch?v=qEic2ZU6taM", "en"
            )
        assert exc_info.value.status_code == 502
        fetch_mock.assert_not_called()
        assert await redis.keys("news:summary:daily:*") == []

    async def test_google_news_link_is_resolved_first(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", "k")
        mocker.patch(
            "outception.news.summary.gnews.resolve",
            return_value="https://www.zeit.de/politik/story",
        )
        fetch_mock = mocker.patch(
            "outception.news.summary.fetch_html", return_value=_soup()
        )
        mocker.patch("outception.news.summary._summarize", return_value="gist")
        gn = "https://news.google.com/rss/articles/CBMiAQ?oc=5"
        assert await summary.get_summary(redis, gn, "en") == "gist"
        fetch_mock.assert_called_once_with("https://www.zeit.de/politik/story")

    async def test_unresolvable_google_news_link_is_fail_marked(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", "k")
        mocker.patch("outception.news.summary.gnews.resolve", return_value=None)
        fetch_mock = mocker.patch("outception.news.summary.fetch_html")
        gn = "https://news.google.com/rss/articles/CBMiAQ?oc=5"
        with pytest.raises(OutceptionError) as exc_info:
            await summary.get_summary(redis, gn, "en")
        assert exc_info.value.status_code == 502
        fetch_mock.assert_not_called()
        marker = summary._FAIL_KEY.format(digest=summary._digest(gn, "en"))
        assert await redis.get(marker) is not None

    async def test_rejects_non_http(self, redis: Redis, mocker: MockerFixture) -> None:
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", "k")
        with pytest.raises(OutceptionError):
            await summary.get_summary(redis, "ftp://example.com/x", "en")


@pytest.mark.asyncio
class TestSummarizeFallback:
    async def test_gemini_first_when_configured(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "GEMINI_API_KEY", "g")
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", "k")
        gemini = mocker.patch(
            "outception.news.summary._summarize_gemini", return_value="from gemini"
        )
        anthropic = mocker.patch("outception.news.summary._summarize_anthropic")
        assert await summary._summarize(redis, "text", "en") == "from gemini"
        gemini.assert_called_once()
        anthropic.assert_not_called()

    async def test_falls_back_to_anthropic(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "GEMINI_API_KEY", "g")
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", "k")
        mocker.patch(
            "outception.news.summary._summarize_gemini",
            side_effect=httpx.HTTPError("quota"),
        )
        anthropic = mocker.patch(
            "outception.news.summary._summarize_anthropic",
            return_value="from claude",
        )
        assert await summary._summarize(redis, "text", "en") == "from claude"
        anthropic.assert_called_once()

    async def test_gemini_failure_without_backup_raises(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "GEMINI_API_KEY", "g")
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", None)
        mocker.patch(
            "outception.news.summary._summarize_gemini",
            side_effect=httpx.HTTPError("quota"),
        )
        with pytest.raises(httpx.HTTPError):
            await summary._summarize(redis, "text", "en")

    async def test_anthropic_only(self, redis: Redis, mocker: MockerFixture) -> None:
        mocker.patch.object(settings, "GEMINI_API_KEY", None)
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", "k")
        anthropic = mocker.patch(
            "outception.news.summary._summarize_anthropic",
            return_value="from claude",
        )
        assert await summary._summarize(redis, "text", "en") == "from claude"
        anthropic.assert_called_once()

    async def test_paid_summary_cap(self, redis: Redis, mocker: MockerFixture) -> None:
        mocker.patch.object(settings, "GEMINI_API_KEY", None)
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", "k")
        mocker.patch.object(settings, "SUMMARY_PAID_DAILY_CAP", 1)
        anthropic = mocker.patch.object(
            summary, "_summarize_anthropic", return_value="from claude"
        )
        assert await summary._summarize(redis, "text", "en") == "from claude"
        with pytest.raises(ValueError, match="paid summary cap"):
            await summary._summarize(redis, "text", "en")
        anthropic.assert_called_once()


@pytest.mark.asyncio
class TestWarmSummary:
    async def test_queue_roundtrip(self, redis: Redis, mocker: MockerFixture) -> None:
        mocker.patch.object(settings, "GEMINI_API_KEY", "g")
        await summary.note_warm_candidate(redis, _URL, "fr")
        assert await summary.pop_warm_candidate(redis) == (_URL, "fr", "viewed")
        assert await summary.pop_warm_candidate(redis) is None

    async def test_urgent_handoff_jumps_a_full_queue(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "GEMINI_API_KEY", "g")
        mocker.patch.object(summary, "_WARM_QUEUE_MAX", 1)
        await redis.delete(summary._WARM_QUEUE_KEY, summary._WARM_URGENT_KEY)
        await summary.note_warm_candidate(redis, f"{_URL}-hero", "en")
        # Hero queue full: a further hero is dropped, a live tap's handoff is
        # taken anyway - and drained first, oldest handoff before newest.
        await summary.note_warm_candidate(redis, f"{_URL}-late", "en")
        await summary.note_warm_candidate(redis, f"{_URL}-tapped", "en", urgent=True)
        await summary.note_warm_candidate(redis, f"{_URL}-tapped2", "en", urgent=True)
        assert await summary.pop_warm_candidate(redis) == (
            f"{_URL}-tapped",
            "en",
            "urgent",
        )
        assert await summary.pop_warm_candidate(redis) == (
            f"{_URL}-tapped2",
            "en",
            "urgent",
        )
        assert await summary.pop_warm_candidate(redis) == (
            f"{_URL}-hero",
            "en",
            "viewed",
        )
        assert await summary.pop_warm_candidate(redis) is None

    async def test_queue_requires_gemini(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "GEMINI_API_KEY", None)
        await summary.note_warm_candidate(redis, _URL, "en")
        assert await summary.pop_warm_candidate(redis) is None

    async def test_warm_generates_gemini_only(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "GEMINI_API_KEY", "g")
        mocker.patch("outception.news.summary.fetch_html", return_value=_soup())
        gemini = mocker.patch(
            "outception.news.summary._summarize_gemini", return_value="warm gist"
        )
        anthropic = mocker.patch("outception.news.summary._summarize_anthropic")
        assert await summary.warm_summary(redis, _URL, "en") == "warmed"
        gemini.assert_called_once()
        anthropic.assert_not_called()
        assert await summary.get_summary(redis, _URL, "en") == "warm gist"

    async def test_warm_skips_cached(self, redis: Redis, mocker: MockerFixture) -> None:
        mocker.patch.object(settings, "GEMINI_API_KEY", "g")
        await redis.set(
            summary._CACHE_KEY.format(digest=summary._digest(_URL, "en")), "done"
        )
        fetch_mock = mocker.patch("outception.news.summary.fetch_html")
        assert await summary.warm_summary(redis, _URL, "en") == "skipped"
        fetch_mock.assert_not_called()

    async def test_warm_respects_warm_cap(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "GEMINI_API_KEY", "g")
        mocker.patch.object(settings, "SUMMARY_WARM_DAILY_CAP", 0)
        fetch_mock = mocker.patch("outception.news.summary.fetch_html")
        assert await summary.warm_summary(redis, _URL, "en") == "unavailable"
        fetch_mock.assert_not_called()

    async def test_speculative_warming_has_its_own_smaller_cap(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        """Summaries and headline translation share the Gemini fleet, and the
        roster sweep was taking 1,192 of the day's 1,216 summaries for articles
        nobody had opened. Speculative warming stops at its own cap; warming
        for a card a reader actually opened carries on."""
        mocker.patch.object(settings, "GEMINI_API_KEY", "g")
        mocker.patch.object(settings, "SUMMARY_PRETAP_DAILY_CAP", 0)
        fetch_mock = mocker.patch("outception.news.summary.fetch_html")
        assert await summary.warm_summary(redis, _URL, "en", "pretap") == "skipped"
        fetch_mock.assert_not_called()

    async def test_viewed_card_warming_ignores_the_speculative_cap(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "GEMINI_API_KEY", "g")
        mocker.patch.object(settings, "SUMMARY_PRETAP_DAILY_CAP", 0)
        mocker.patch("outception.news.summary.fetch_html", return_value=_soup())
        mocker.patch(
            "outception.news.summary._summarize_gemini", return_value="warm gist"
        )
        assert await summary.warm_summary(redis, _URL, "en", "viewed") == "warmed"

    async def test_speculative_spend_is_counted_separately(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "GEMINI_API_KEY", "g")
        mocker.patch("outception.news.summary.fetch_html", return_value=_soup())
        mocker.patch(
            "outception.news.summary._summarize_gemini", return_value="warm gist"
        )
        day = _today()
        assert await summary.warm_summary(redis, _URL, "en", "pretap") == "warmed"
        assert await _counter(redis, summary._PRETAP_DAILY_KEY.format(day=day)) == 1
        # A viewed-card warm charges the warm budget but not the speculative one.
        assert (
            await summary.warm_summary(
                redis, "https://example.com/other", "en", "viewed"
            )
            == "warmed"
        )
        assert await _counter(redis, summary._PRETAP_DAILY_KEY.format(day=day)) == 1
        assert await _counter(redis, summary._WARM_DAILY_KEY.format(day=day)) == 2

    async def test_warm_stands_down_for_live_budget(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "GEMINI_API_KEY", "g")
        mocker.patch.object(settings, "SUMMARY_DAILY_CAP", 10)
        from datetime import UTC, datetime

        day = datetime.now(UTC).strftime("%Y%m%d")
        await redis.set(summary._DAILY_KEY.format(day=day), "6")
        fetch_mock = mocker.patch("outception.news.summary.fetch_html")
        assert await summary.warm_summary(redis, _URL, "en") == "unavailable"
        fetch_mock.assert_not_called()

    async def test_minute_full_pool_requeues_instead_of_discarding(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        """A minute with no free slot is transient, not "nothing to do".
        Returning "skipped" DISCARDED the candidate - it has already been
        popped off the queue - so a live tap's urgent handoff was destroyed
        and the reader's re-tap paid full cold generation again."""
        mocker.patch.object(settings, "GEMINI_API_KEY", "g")
        mocker.patch(
            "outception.news.summary.gemini.acquire", AsyncMock(return_value=None)
        )
        mocker.patch(
            "outception.news.summary.free_llm.acquire", AsyncMock(return_value=None)
        )
        fetch_mock = mocker.patch("outception.news.summary.fetch_html")
        # "unavailable" is the outcome the warm task requeues on (see tasks.py).
        assert await summary.warm_summary(redis, _URL, "en") == "unavailable"
        fetch_mock.assert_not_called()

    async def test_warm_failure_sets_marker(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "GEMINI_API_KEY", "g")
        # Earlier tests may have benched key 0 in this shared fake redis.
        for i in range(5):
            await redis.delete(f"news:gemini:cd:{i}")
        mocker.patch(
            "outception.news.summary.fetch_html",
            side_effect=NewsFetchError("blocked"),
        )
        mocker.patch(
            "outception.news.summary._reader_text",
            side_effect=NewsFetchError("reader blocked"),
        )
        assert await summary.warm_summary(redis, _URL, "en") == "failed"
        marker = summary._FAIL_KEY.format(digest=summary._digest(_URL, "en"))
        assert await redis.get(marker) is not None


@pytest.mark.asyncio
class TestReaderFallback:
    async def test_blocked_publisher_uses_reader(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch(
            "outception.news.summary.fetch_html",
            side_effect=NewsFetchError("HTTP 403 from https://www.rte.ie/x"),
        )
        reader = mocker.patch(
            "outception.news.summary._reader_text", return_value="word " * 200
        )
        text = await summary._article_text("https://www.rte.ie/x")
        assert len(text) > summary._MIN_ARTICLE_CHARS
        reader.assert_called_once_with("https://www.rte.ie/x")

    async def test_teaser_page_uses_reader(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch(
            "outception.news.summary.fetch_html",
            return_value=BeautifulSoup("<p>short teaser</p>", "lxml"),
        )
        reader = mocker.patch(
            "outception.news.summary._reader_text", return_value="word " * 200
        )
        assert len(await summary._article_text("https://x.test/a")) > 350
        reader.assert_called_once()

    async def test_unsafe_url_never_reaches_reader(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch(
            "outception.news.summary.fetch_html",
            side_effect=UnsafeURLError("unsafe or unresolvable URL: http://10.0.0.1/"),
        )
        reader = mocker.patch("outception.news.summary._reader_text")
        with pytest.raises(UnsafeURLError):
            await summary._article_text("http://10.0.0.1/")
        reader.assert_not_called()

    async def test_flag_off_keeps_old_behaviour(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "READER_FALLBACK_ENABLED", False)
        mocker.patch(
            "outception.news.summary.fetch_html",
            side_effect=NewsFetchError("HTTP 403 from https://www.rte.ie/x"),
        )
        reader = mocker.patch("outception.news.summary._reader_text")
        with pytest.raises(NewsFetchError, match="403"):
            await summary._article_text("https://www.rte.ie/x")
        reader.assert_not_called()


@pytest.mark.asyncio
class TestFailureMemory:
    async def test_transient_failure_is_short_lived(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", "k")
        mocker.patch.object(settings, "READER_FALLBACK_ENABLED", False)
        mocker.patch(
            "outception.news.summary.fetch_html",
            side_effect=NewsFetchError("timed out"),
        )
        with pytest.raises(OutceptionError):
            await summary.get_summary(redis, _URL, "en")
        marker = summary._FAIL_KEY.format(digest=summary._digest(_URL, "en"))
        assert await redis.ttl(marker) <= summary._FAIL_TTL_SECONDS
        assert (
            await redis.get(summary._HOST_FAIL_KEY.format(host="example.com")) is None
        )

    async def test_not_an_article_is_remembered_for_a_day(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", "k")
        mocker.patch("outception.news.summary.fetch_html", return_value=_soup())
        mocker.patch("outception.news.summary._summarize", return_value="NO_ARTICLE")
        with pytest.raises(OutceptionError):
            await summary.get_summary(redis, _URL, "en")
        marker = summary._FAIL_KEY.format(digest=summary._digest(_URL, "en"))
        assert await redis.ttl(marker) > summary._FAIL_TTL_SECONDS
        failures = await redis.get(summary._HOST_FAIL_KEY.format(host="example.com"))
        assert int(failures or 0) == 1

    async def test_short_page_is_not_held_against_the_publisher(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", "k")
        mocker.patch.object(settings, "READER_FALLBACK_ENABLED", False)
        mocker.patch(
            "outception.news.summary.fetch_html",
            return_value=BeautifulSoup(
                "<html><body><p>Clip.</p></body></html>", "lxml"
            ),
        )
        with pytest.raises(OutceptionError):
            await summary.get_summary(redis, _URL, "en")
        marker = summary._FAIL_KEY.format(digest=summary._digest(_URL, "en"))
        # Nor against the article: a page that served only a stub this once
        # (slow render, JS-heavy) heals, so it gets the short retry window
        # rather than the day-long one definitive failures earn.
        assert 0 < await redis.ttl(marker) <= summary._FAIL_TTL_SECONDS
        assert (
            await redis.get(summary._HOST_FAIL_KEY.format(host="example.com")) is None
        )

    async def test_publisher_brake_after_repeated_definitive_failures(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", "k")
        fetch_mock = mocker.patch(
            "outception.news.summary.fetch_html", return_value=_soup()
        )
        mocker.patch("outception.news.summary._summarize", return_value="NO_ARTICLE")
        for i in range(summary._HOST_FAIL_LIMIT):
            with pytest.raises(OutceptionError):
                await summary.get_summary(redis, f"{_URL}-{i}", "en")
        assert fetch_mock.call_count == summary._HOST_FAIL_LIMIT
        with pytest.raises(OutceptionError):
            await summary.get_summary(redis, f"{_URL}-fresh", "en")
        assert fetch_mock.call_count == summary._HOST_FAIL_LIMIT
        await _know(redis, f"{_URL}-other", "https://other.example/x")
        assert await summary.is_available(redis, f"{_URL}-other", "en") is False
        assert await summary.is_available(redis, "https://other.example/x", "en")

    async def test_success_clears_publisher_brake(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", "k")
        await redis.set(summary._HOST_FAIL_KEY.format(host="example.com"), "2")
        mocker.patch("outception.news.summary.fetch_html", return_value=_soup())
        mocker.patch("outception.news.summary._summarize", return_value="Fine.")
        assert await summary.get_summary(redis, _URL, "en") == "Fine."
        assert (
            await redis.get(summary._HOST_FAIL_KEY.format(host="example.com")) is None
        )


@pytest.mark.asyncio
class TestIsAvailable:
    async def test_unknown_article_is_available(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", "k")
        fetch_mock = mocker.patch("outception.news.summary.fetch_html")
        await _know(redis, _URL)
        assert await summary.is_available(redis, _URL, "en") is True
        fetch_mock.assert_not_called()
        assert await redis.keys("news:summary:daily:*") == []

    async def test_never_served_url_is_not_available(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", "k")
        assert not await summary.is_available(redis, _URL, "en")

    async def test_known_negatives(self, redis: Redis, mocker: MockerFixture) -> None:
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", "k")
        await _know(redis, _URL)
        assert not await summary.is_available(redis, "https://youtu.be/abc", "en")
        assert not await summary.is_available(redis, "ftp://example.com/x", "en")
        await redis.set(
            summary._FAIL_KEY.format(digest=summary._digest(_URL, "en")), "1"
        )
        assert not await summary.is_available(redis, _URL, "en")
        assert await summary.is_available(redis, _URL, "de")

    async def test_cached_summary_is_available(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", "k")
        await _know(redis, _URL)
        await redis.set(
            summary._CACHE_KEY.format(digest=summary._digest(_URL, "en")), "S"
        )
        assert await summary.is_available(redis, _URL, "en") is True

    async def test_unavailable_when_gemini_out_and_paid_cap_reached(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        from outception.news import gemini

        mocker.patch.object(settings, "GEMINI_API_KEY", "g")
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", "k")
        mocker.patch.object(settings, "SUMMARY_PAID_DAILY_CAP", 25)
        await _know(redis, _URL)
        # Gemini benched for the day, paid budget spent: no provider can run.
        await redis.set(gemini._COOLDOWN_KEY.format(i=0), "1")
        await redis.set(summary._PAID_DAILY_KEY.format(day=_today()), "25")
        assert await summary.is_available(redis, _URL, "en") is False
        # Paid budget restored -> available again.
        await redis.set(summary._PAID_DAILY_KEY.format(day=_today()), "10")
        assert await summary.is_available(redis, _URL, "en") is True
        # Or Gemini back -> available even with the paid cap spent.
        await redis.set(summary._PAID_DAILY_KEY.format(day=_today()), "25")
        await redis.delete(gemini._COOLDOWN_KEY.format(i=0))
        assert await summary.is_available(redis, _URL, "en") is True

    async def test_not_configured_or_capped(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", None)
        mocker.patch.object(settings, "GEMINI_API_KEY", None)
        assert not await summary.is_available(redis, _URL, "en")
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", "k")
        mocker.patch.object(settings, "SUMMARY_DAILY_CAP", 0)
        assert not await summary.is_available(redis, _URL, "en")

    async def test_google_news_uses_cached_resolution(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", "k")
        url = "https://news.google.com/rss/articles/CBMiAWE?oc=5"
        await _know(redis, url)
        mocker.patch("outception.news.gnews.cached_resolution", return_value=None)
        assert await summary.is_available(redis, url, "en") is True
        mocker.patch("outception.news.gnews.cached_resolution", return_value="")
        assert await summary.is_available(redis, url, "en") is False


@pytest.mark.asyncio
class TestPublisherTeaser:
    async def test_feed_teaser_when_article_is_blocked(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", "k")
        mocker.patch.object(settings, "READER_FALLBACK_ENABLED", False)
        mocker.patch(
            "outception.news.summary.fetch_html",
            side_effect=NewsFetchError("blocked"),
        )
        translate_mock = mocker.patch(
            "outception.news.translate.translate_texts_with_status",
            AsyncMock(
                side_effect=lambda redis, texts, lang, **kw: (list(texts), False)
            ),
        )
        from outception.news import cache as news_cache
        from outception.news.schemas import NewsItem

        await news_cache.remember_items(
            redis,
            [
                NewsItem(
                    id=_URL,
                    title="T",
                    url=_URL,
                    teaser="The publisher standfirst, forty chars long.",
                )
            ],
        )
        result = await summary.get_summary_result(redis, _URL, "de")
        assert result.kind == "teaser"
        assert result.text.startswith("The publisher standfirst")
        assert result.translation_pending is False
        translate_mock.assert_awaited_once()
        # Cached: the next tap does not translate again.
        again = await summary.get_summary_result(redis, _URL, "de")
        assert again == result
        translate_mock.assert_awaited_once()
        assert await summary.is_available(redis, _URL, "de") is True

    async def test_pending_translation_is_flagged_and_not_cached(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        """A teaser whose translation is still running is served in the
        original language ONCE, flagged so the client can poll, and never
        cached - the next tap must pick up the translated line."""
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", "k")
        mocker.patch.object(settings, "READER_FALLBACK_ENABLED", False)
        mocker.patch(
            "outception.news.summary.fetch_html",
            side_effect=NewsFetchError("blocked"),
        )
        translate_mock = mocker.patch(
            "outception.news.translate.translate_texts_with_status",
            AsyncMock(side_effect=lambda redis, texts, lang, **kw: (list(texts), True)),
        )
        from outception.news import cache as news_cache
        from outception.news.schemas import NewsItem

        await news_cache.remember_items(
            redis,
            [
                NewsItem(
                    id=_URL,
                    title="T",
                    url=_URL,
                    teaser="The publisher standfirst, forty chars long.",
                )
            ],
        )
        result = await summary.get_summary_result(redis, _URL, "de")
        assert result.kind == "teaser"
        assert result.translation_pending is True
        assert await summary.has_cached(redis, _URL, "de") is False
        # Not cached: the next tap asks the translator again.
        await summary.get_summary_result(redis, _URL, "de")
        assert translate_mock.await_count == 2

    async def test_stream_marks_an_untranslated_teaser_pending(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        """The web reads summaries over the stream, which had no way to say
        'still translating', so it showed the publisher's English line and
        never asked again."""
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", "k")
        mocker.patch.object(settings, "READER_FALLBACK_ENABLED", False)
        mocker.patch(
            "outception.news.summary.fetch_html",
            side_effect=NewsFetchError("blocked"),
        )
        mocker.patch(
            "outception.news.translate.translate_texts_with_status",
            AsyncMock(side_effect=lambda redis, texts, lang, **kw: (list(texts), True)),
        )
        from outception.news import cache as news_cache
        from outception.news.schemas import NewsItem

        await news_cache.remember_items(
            redis,
            [
                NewsItem(
                    id=_URL,
                    title="T",
                    url=_URL,
                    teaser="The publisher standfirst, forty chars long.",
                )
            ],
        )
        await redis.set(
            summary._FAIL_KEY.format(digest=summary._digest(_URL, "de")), "1"
        )
        events = [e async for e in summary.stream_summary(redis, _URL, "de")]
        assert events == [
            {
                "text": "The publisher standfirst, forty chars long.",
                "kind": "teaser",
                "pending": True,
            }
        ]

    async def test_stream_omits_pending_for_a_finished_result(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        """A translated teaser carries no flag, so the browser stops asking."""
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", "k")
        mocker.patch.object(settings, "READER_FALLBACK_ENABLED", False)
        mocker.patch(
            "outception.news.summary.fetch_html",
            side_effect=NewsFetchError("blocked"),
        )
        mocker.patch(
            "outception.news.translate.translate_texts_with_status",
            AsyncMock(
                side_effect=lambda redis, texts, lang, **kw: (["Der Vorspann."], False)
            ),
        )
        from outception.news import cache as news_cache
        from outception.news.schemas import NewsItem

        await news_cache.remember_items(
            redis,
            [
                NewsItem(
                    id=_URL,
                    title="T",
                    url=_URL,
                    teaser="The publisher standfirst, forty chars long.",
                )
            ],
        )
        await redis.set(
            summary._FAIL_KEY.format(digest=summary._digest(_URL, "de")), "1"
        )
        events = [e async for e in summary.stream_summary(redis, _URL, "de")]
        assert events == [{"text": "Der Vorspann.", "kind": "teaser"}]

    async def test_page_description_when_feed_has_none(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", "k")
        mocker.patch.object(settings, "READER_FALLBACK_ENABLED", False)
        html = (
            '<html><head><meta property="og:description" content="A paywalled '
            'article about the harbour expansion plan and its critics."></head>'
            "<body><p>Subscribe to read.</p></body></html>"
        )
        mocker.patch(
            "outception.news.summary.fetch_html",
            return_value=BeautifulSoup(html, "lxml"),
        )
        mocker.patch(
            "outception.news.translate.translate_texts",
            AsyncMock(side_effect=lambda redis, texts, lang, **kw: list(texts)),
        )
        result = await summary.get_summary_result(redis, _URL, "en")
        assert result.kind == "teaser"
        assert "harbour expansion" in result.text

    async def test_no_teaser_still_unavailable(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", "k")
        mocker.patch.object(settings, "READER_FALLBACK_ENABLED", False)
        mocker.patch(
            "outception.news.summary.fetch_html",
            side_effect=NewsFetchError("blocked"),
        )
        with pytest.raises(OutceptionError) as exc_info:
            await summary.get_summary_result(redis, _URL, "en")
        assert exc_info.value.status_code == 502
        assert await summary.is_available(redis, _URL, "en") is False

    async def test_feed_teaser_served_even_when_fail_marked(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", "k")
        mocker.patch(
            "outception.news.translate.translate_texts",
            AsyncMock(side_effect=lambda redis, texts, lang, **kw: list(texts)),
        )
        fetch_mock = mocker.patch("outception.news.summary.fetch_html")
        from outception.news import cache as news_cache
        from outception.news.schemas import NewsItem

        await redis.set(
            summary._FAIL_KEY.format(digest=summary._digest(_URL, "en")), "1"
        )
        await news_cache.remember_items(
            redis,
            [
                NewsItem(
                    id=_URL,
                    title="T",
                    url=_URL,
                    teaser="Standfirst kept by the feed, forty characters.",
                )
            ],
        )
        result = await summary.get_summary_result(redis, _URL, "en")
        assert result.kind == "teaser"
        fetch_mock.assert_not_called()


@pytest.mark.asyncio
class TestStreamSummary:
    async def _events(self, redis: Redis, url: str = _URL) -> list[dict[str, object]]:
        return [event async for event in summary.stream_summary(redis, url, "en")]

    async def test_streams_deltas_and_caches(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", "k")
        mocker.patch.object(settings, "GEMINI_API_KEY", None)
        mocker.patch("outception.news.summary.fetch_html", return_value=_soup())

        async def stream(text: str, lang: str):  # type: ignore[no-untyped-def]
            for piece in [
                "The council ",
                "backed the plan ",
                "after a week of talks — ",
                "critics object.",
            ]:
                yield piece

        mocker.patch.object(summary, "_stream_anthropic", stream)
        events = await self._events(redis)
        assert events[-1] == {"done": True, "kind": "summary"}
        text = "".join(str(e["delta"]) for e in events if "delta" in e)
        assert (
            text
            == "The council backed the plan after a week of talks , critics object."
        )
        assert (await summary.get_summary_result(redis, _URL, "en")).text == text
        assert await redis.keys("news:summary:pending:*") == []

    async def test_no_article_sentinel_is_held_back(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", "k")
        mocker.patch.object(settings, "GEMINI_API_KEY", None)
        mocker.patch("outception.news.summary.fetch_html", return_value=_soup())

        async def stream(text: str, lang: str):  # type: ignore[no-untyped-def]
            yield "NO_ARTICLE"

        mocker.patch.object(summary, "_stream_anthropic", stream)
        events = await self._events(redis)
        assert events == [{"error": "unavailable"}]

    async def test_cached_result_arrives_whole(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", "k")
        await redis.set(
            summary._CACHE_KEY.format(digest=summary._digest(_URL, "en")), "S"
        )
        assert await self._events(redis) == [{"text": "S", "kind": "summary"}]

    async def test_teaser_when_article_blocked(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "ANTHROPIC_API_KEY", "k")
        mocker.patch.object(settings, "READER_FALLBACK_ENABLED", False)
        mocker.patch(
            "outception.news.summary.fetch_html",
            side_effect=NewsFetchError("blocked"),
        )
        mocker.patch(
            "outception.news.translate.translate_texts",
            AsyncMock(side_effect=lambda redis, texts, lang, **kw: list(texts)),
        )
        from outception.news import cache as news_cache
        from outception.news.schemas import NewsItem

        await news_cache.remember_items(
            redis,
            [
                NewsItem(
                    id=_URL,
                    title="T",
                    url=_URL,
                    teaser="The publisher standfirst, forty chars long.",
                )
            ],
        )
        events = await self._events(redis)
        assert events[0]["kind"] == "teaser"


class TestTeaserJunkFilter:
    def test_error_page_text_is_never_a_teaser(self) -> None:
        # CoinDesk's feed served this as a description and the card presented
        # it as "the publisher's own summary".
        junk = "Warning: Target URL returned error 429: Too Many Requests"
        assert summary._clean_teaser(junk) is None
        assert (
            summary._clean_teaser(
                "Please enable JavaScript and cookies to continue viewing."
            )
            is None
        )

    def test_cdn_error_pages_are_junk(self) -> None:
        """Reached a Croatian card as "the publisher's own summary" - and was
        translated first, so an error page cost model budget to print."""
        akamai = (
            "You don't have permission to access "
            '"http://www.13wmaz.com/article/news/local/dublin/x" on this '
            "server. Reference #18.e3dd717.1789030676.516f36f2 "
            "https://errors.edgesuite.net/18.e3dd717.1789030676.516f36f2"
        )
        for body in (
            akamai,
            "The request could not be satisfied. Request blocked. We can not "
            "connect to the server for this app or website at this time.",
            "Access to this page has been denied because we believe you are "
            "using automation tools to browse the website.",
            "You do not have permission to access this document on this "
            "server, and there is no index page available for it.",
            "Reference #18.e3dd717.1789030676.516f36f2 was recorded for this "
            "request by the edge server handling it today.",
        ):
            assert summary._clean_teaser(body) is None, body[:40]

    def test_prose_that_merely_sounds_like_an_error_passes(self) -> None:
        """The patterns must match the machine wording, not the words: a
        standfirst about parking permission is a real standfirst."""
        for body in (
            "The council said residents do not have permission to park on "
            "the green, a rule it has enforced since 2019 across the estate.",
            "Developers do not have permission to build on the site until "
            "the appeal concludes, the board confirmed in a statement.",
            "The report made reference to a 2019 study of housing density in "
            "the greater Dublin area and its effect on commuting times.",
            "The minister denied claims that the department had misled the "
            "committee about the cost of the new hospital wing.",
        ):
            assert summary._clean_teaser(body) is not None, body[:40]

    def test_real_standfirst_passes(self) -> None:
        text = (
            "The publisher standfirst, forty characters long at least, "
            "describing the story."
        )
        assert summary._clean_teaser(text) == text


@pytest.mark.asyncio
class TestStreamDeadlines:
    """Only the FIRST chunk used to be deadlined. httpx times out per read, not
    per stream, so a model trickling tokens had no ceiling - and the
    duplicate-tap wait is derived from that ceiling, so a second reader could
    time out while the summary they were waiting for was still being written."""

    @staticmethod
    async def _drain(stream: object, first: float, total: float) -> list[str]:
        return [
            chunk
            async for chunk in summary._started_in_time(stream, first, total)  # type: ignore[arg-type]
        ]

    async def test_whole_stream_is_bounded_not_just_the_first_chunk(self) -> None:
        async def trickle():  # type: ignore[no-untyped-def]
            yield "The "  # first chunk lands at once
            for _ in range(20):
                await asyncio.sleep(0.05)
                yield "and on "

        with pytest.raises(summary.LiveDeadlinePassed, match="finish writing"):
            await self._drain(trickle(), 1.0, 0.15)

    async def test_a_stream_that_finishes_in_budget_is_untouched(self) -> None:
        async def quick():  # type: ignore[no-untyped-def]
            yield "A "
            yield "short "
            yield "summary."

        assert await self._drain(quick(), 1.0, 5.0) == ["A ", "short ", "summary."]

    async def test_first_chunk_deadline_still_applies(self) -> None:
        async def stalls():  # type: ignore[no-untyped-def]
            await asyncio.sleep(5)
            yield "never"

        with pytest.raises(summary.LiveDeadlinePassed, match="start writing"):
            await self._drain(stalls(), 0.05, 10.0)


class TestSummaryDeadlineRelationships:
    def test_waiter_outlasts_the_slower_of_the_two_leader_paths(self) -> None:
        """The wait is derived from four other deadlines; deriving it from the
        non-streaming budget alone left it shorter than a streaming leader."""
        streaming = summary._LIVE_ARTICLE_SECONDS + summary._LIVE_STREAM_SECONDS
        non_streaming = summary._LIVE_ARTICLE_SECONDS + summary._LIVE_MODEL_SECONDS
        assert summary._PENDING_WAIT_SECONDS > max(streaming, non_streaming)
        # And the single-flight marker must outlive the wait watching it, or
        # the marker expires and duplicate taps each pay for a generation.
        assert summary._PENDING_WAIT_SECONDS < summary._PENDING_TTL_SECONDS
