from collections.abc import AsyncIterator

import httpx
import pytest
from pytest_mock import MockerFixture

from outception.news.fetch import (
    NewsFetchError,
    _check_redirect,
    _get,
    fetch_text,
    parse_rss,
)


def _redirect_response(location: str) -> httpx.Response:
    return httpx.Response(
        status_code=302,
        headers={"location": location},
        request=httpx.Request("GET", "https://feed.example.com/rss"),
    )


@pytest.mark.asyncio
class TestRedirectGuard:
    async def test_rejects_redirect_to_metadata_ip(self) -> None:
        # A source must not be able to bounce the fetcher to an internal host.
        with pytest.raises(NewsFetchError):
            await _check_redirect(_redirect_response("http://169.254.169.254/"))

    async def test_rejects_redirect_to_loopback(self) -> None:
        with pytest.raises(NewsFetchError):
            await _check_redirect(_redirect_response("http://127.0.0.1:8000/"))

    async def test_allows_public_redirect(self) -> None:
        await _check_redirect(_redirect_response("https://example.com/feed"))

    async def test_ignores_non_redirect(self) -> None:
        ok = httpx.Response(
            status_code=200,
            request=httpx.Request("GET", "https://example.com/rss"),
        )
        await _check_redirect(ok)


class _FakeStream:
    """Mimics the async context manager returned by httpx's client.stream()."""

    status_code = 200
    headers: dict[str, str] = {}
    charset_encoding: str | None = None
    request = httpx.Request("GET", "https://feed.example.com/rss")

    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = chunks

    async def __aenter__(self) -> "_FakeStream":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def aiter_bytes(self) -> AsyncIterator[bytes]:
        for chunk in self._chunks:
            yield chunk


@pytest.mark.asyncio
class TestSizeCap:
    async def test_oversized_body_is_rejected_while_streaming(
        self, mocker: MockerFixture
    ) -> None:
        # 6 MB streamed in 1 MB chunks must abort past the 5 MB cap rather than
        # buffer the whole body.
        chunks = [b"x" * (1024 * 1024) for _ in range(6)]
        mocker.patch("outception.news.fetch.is_fetchable_async", return_value=True)
        mocker.patch(
            "outception.news.fetch._client.stream", return_value=_FakeStream(chunks)
        )
        with pytest.raises(NewsFetchError, match="too large"):
            await _get("https://feed.example.com/rss")

    async def test_within_cap_returns_content(self, mocker: MockerFixture) -> None:
        mocker.patch("outception.news.fetch.is_fetchable_async", return_value=True)
        mocker.patch(
            "outception.news.fetch._client.stream",
            return_value=_FakeStream([b"hello ", b"world"]),
        )
        content, charset = await _get("https://feed.example.com/rss")
        assert content == b"hello world"
        assert charset is None

    async def test_unsafe_initial_url_rejected(self, mocker: MockerFixture) -> None:
        mocker.patch("outception.news.fetch.is_fetchable_async", return_value=False)
        with pytest.raises(NewsFetchError, match="unsafe"):
            await fetch_text("http://169.254.169.254/")


class TestParseRss:
    def test_decodes_double_encoded_entities_in_titles(self) -> None:
        # The Verge (and others) double-encode entities, so feedparser hands us a
        # title still holding numeric entities like &#8217;. parse_rss must decode
        # them so the headline — and its machine translation — reads cleanly.
        feed = """<?xml version="1.0"?>
        <rss version="2.0"><channel>
          <item>
            <title>Apple&amp;#8217;s OLED iPad Mini upgrade is on the way</title>
            <link>https://example.com/apple</link>
          </item>
        </channel></rss>"""
        items = parse_rss(feed)
        assert len(items) == 1
        assert items[0].title == "Apple’s OLED iPad Mini upgrade is on the way"

    def test_leaves_plain_titles_untouched(self) -> None:
        feed = """<?xml version="1.0"?>
        <rss version="2.0"><channel>
          <item>
            <title>Markets rally as inflation cools</title>
            <link>https://example.com/markets</link>
          </item>
        </channel></rss>"""
        items = parse_rss(feed)
        assert len(items) == 1
        assert items[0].title == "Markets rally as inflation cools"
