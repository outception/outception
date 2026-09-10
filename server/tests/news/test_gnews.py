import base64

import pytest
from pytest_mock import MockerFixture

from outception.news import gnews
from outception.redis import Redis

_BATCH_REPLY = (
    ")]}'\n\n"
    '[["wrb.fr","Fbv4je","[\\"garturlres\\",\\"https://www.zeit.de/politik/story\\",1]",'
    'null,null,null,""],["di",10],["af.httprm",9,"353",12]]\n'
)


def _inline_id(url: str) -> str:
    body = url.encode()
    raw = b"\x08\x13\x22" + bytes([len(body)]) + body + b"\xd2\x01\x00"
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


class TestDecoding:
    def test_article_id_from_every_link_shape(self) -> None:
        for path in ("rss/articles", "articles", "read"):
            url = f"https://news.google.com/{path}/CBMiAQabc?oc=5"
            assert gnews.article_id(url) == "CBMiAQabc"
        assert gnews.article_id("https://news.google.com/topstories") is None
        assert gnews.is_google_news_url("https://news.google.com/rss/articles/x")
        assert not gnews.is_google_news_url("https://www.bbc.co.uk/news/x")

    def test_inline_ids_decode_locally(self) -> None:
        assert (
            gnews.decode_inline(_inline_id("https://example.com/story"))
            == "https://example.com/story"
        )

    def test_current_format_needs_remote(self) -> None:
        assert gnews.decode_inline(_inline_id("AU_yqLabc")) is None
        assert gnews.decode_inline("not base64 at all!") is None

    def test_extract_url_from_batch_reply(self) -> None:
        assert gnews._extract_url(_BATCH_REPLY) == "https://www.zeit.de/politik/story"
        assert gnews._extract_url(')]}\'\n\n[["wrb.fr","Fbv4je",null]]') is None


@pytest.mark.asyncio
class TestResolve:
    async def test_caches_resolved_url(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        remote = mocker.patch.object(
            gnews, "_decode_remote", return_value="https://www.zeit.de/politik/story"
        )
        url = "https://news.google.com/rss/articles/CBMiAQabc?oc=5"
        assert await gnews.resolve(redis, url) == "https://www.zeit.de/politik/story"
        assert await gnews.resolve(redis, url) == "https://www.zeit.de/politik/story"
        remote.assert_called_once()

    async def test_failure_is_cached_negatively(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        remote = mocker.patch.object(gnews, "_decode_remote", return_value=None)
        url = "https://news.google.com/rss/articles/CBMiAQabc?oc=5"
        assert await gnews.resolve(redis, url) is None
        assert await gnews.resolve(redis, url) is None
        remote.assert_called_once()

    async def test_inline_id_never_calls_google(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        remote = mocker.patch.object(gnews, "_decode_remote")
        url = f"https://news.google.com/rss/articles/{_inline_id('https://example.com/a')}?oc=5"
        assert await gnews.resolve(redis, url) == "https://example.com/a"
        remote.assert_not_called()
