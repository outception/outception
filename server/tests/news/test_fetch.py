import time
from collections.abc import AsyncIterator

import httpx
import pytest
from pytest_mock import MockerFixture

from outception.news.fetch import (
    NewsFetchError,
    StaleFeedError,
    _get,
    _reject_private_peer,
    _vet_response,
    fetch_text,
    parse_rss,
    parse_rss_async,
)
from outception.news.schemas import NewsItem
from outception.news.sources import feeds


class _PeerStream:
    """Stands in for httpx's network stream, which exposes the live socket."""

    def __init__(self, peer: str) -> None:
        self._peer = peer

    def get_extra_info(self, name: str) -> object | None:
        if name != "socket":
            return None
        return _PeerSocket(self._peer)


class _PeerSocket:
    def __init__(self, peer: str) -> None:
        self._peer = peer

    def getpeername(self) -> tuple[str, int]:
        return (self._peer, 443)


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
            await _vet_response(_redirect_response("http://169.254.169.254/"))

    async def test_rejects_redirect_to_loopback(self) -> None:
        with pytest.raises(NewsFetchError):
            await _vet_response(_redirect_response("http://127.0.0.1:8000/"))

    async def test_allows_public_redirect(self, mocker: MockerFixture) -> None:
        # A redirect to a public host is allowed. Stub the SSRF/DNS check so the
        # guard's allow-path is exercised without a live DNS lookup (the blocked
        # cases above use IP literals and need no resolution).
        mocker.patch(
            "outception.news.fetch.is_fetchable_async",
            return_value=True,
        )
        await _vet_response(_redirect_response("https://example.com/feed"))

    async def test_ignores_non_redirect(self) -> None:
        ok = httpx.Response(
            status_code=200,
            request=httpx.Request("GET", "https://example.com/rss"),
        )
        await _vet_response(ok)


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
        # them so the headline - and its machine translation - reads cleanly.
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

    @pytest.mark.asyncio
    async def test_async_parse_matches_sync(self) -> None:
        feed = """<?xml version="1.0"?>
        <rss version="2.0"><channel>
          <item>
            <title>Markets rally as inflation cools</title>
            <link>https://example.com/markets</link>
          </item>
        </channel></rss>"""
        assert await parse_rss_async(feed) == parse_rss(feed)


class TestFeedTeaser:
    def test_description_becomes_teaser(self) -> None:
        from outception.news.fetch import parse_rss

        feed = (
            "<rss><channel><item><title>Harbour plan approved</title>"
            "<link>https://example.com/a</link>"
            "<description>&lt;p&gt;The council backed the harbour expansion after a "
            "week of hearings.&lt;/p&gt;</description></item>"
            "<item><title>Short</title><link>https://example.com/b</link>"
            "<description>Short</description></item>"
            "<item><title>G</title><link>https://news.google.com/rss/articles/x</link>"
            "<description>&lt;a href=x&gt;Headline&lt;/a&gt; - Publisher, long enough text here</description></item>"
            "</channel></rss>"
        )
        items = parse_rss(feed)
        assert (
            items[0].teaser
            == "The council backed the harbour expansion after a week of hearings."
        )
        assert items[1].teaser is None
        assert items[2].teaser is None
        assert "teaser" not in items[0].model_dump(by_alias=True, exclude_none=True)


class TestAbandonedFeeds:
    """A publisher can stop posting without taking the feed down: it keeps
    answering 200 with a well-formed body, so only the item dates give it away."""

    def _item(self, pub: int | None) -> NewsItem:
        return NewsItem(id="i", title="T", url="https://example.com/a", pub_date=pub)

    def _ms(self, days_ago: float) -> int:
        return int((time.time() - days_ago * 86400) * 1000)

    def test_every_item_past_the_horizon(self) -> None:
        old = [self._item(self._ms(400)), self._item(self._ms(900))]
        assert feeds._abandoned(old)

    def test_a_single_recent_item_is_enough(self) -> None:
        assert not feeds._abandoned(
            [self._item(self._ms(400)), self._item(self._ms(1))]
        )

    def test_undated_feeds_are_left_alone(self) -> None:
        assert not feeds._abandoned([self._item(None), self._item(None)])

    def test_the_error_still_reads_as_a_fetch_failure(self) -> None:
        assert issubclass(StaleFeedError, NewsFetchError)


class TestPeerAddressGuard:
    """The name-based guard resolves DNS, then httpx resolves again to connect.
    A resolver that answers differently the second time (public, then internal)
    would slip past it, so the socket's real peer is checked as well."""

    def _response(self, peer: str | None) -> httpx.Response:
        response = httpx.Response(200, request=httpx.Request("GET", "https://a.test/"))
        if peer is not None:
            response.extensions["network_stream"] = _PeerStream(peer)
        return response

    def test_public_peer_passes(self) -> None:
        _reject_private_peer(self._response("93.184.216.34"))

    def test_loopback_peer_is_refused(self) -> None:
        with pytest.raises(NewsFetchError):
            _reject_private_peer(self._response("127.0.0.1"))

    def test_metadata_peer_is_refused(self) -> None:
        with pytest.raises(NewsFetchError):
            _reject_private_peer(self._response("169.254.169.254"))

    def test_private_ipv6_peer_is_refused(self) -> None:
        with pytest.raises(NewsFetchError):
            _reject_private_peer(self._response("::1"))

    def test_unknown_peer_defers_to_the_name_guard(self) -> None:
        _reject_private_peer(self._response(None))
