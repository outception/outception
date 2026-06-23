import pytest

from polar.news.schemas import NewsItem


class TestNewsItemUrlSafety:
    @pytest.mark.parametrize(
        "url",
        [
            "javascript:alert(1)",
            "JavaScript:alert(1)",
            "data:text/html,<script>alert(1)</script>",
            "vbscript:msgbox(1)",
            "//evil.example.com",
            "/relative/path",
        ],
    )
    def test_unsafe_url_is_neutralized(self, url: str) -> None:
        # Untrusted feed content must never reach an <a href> as a non-http(s)
        # URL, or it becomes a clickable XSS vector.
        item = NewsItem(id="i", title="t", url=url, mobile_url=url)
        assert item.url == ""
        assert item.mobile_url == ""

    @pytest.mark.parametrize(
        "url",
        ["http://example.com/a", "https://example.com/a?b=c#d"],
    )
    def test_http_url_is_preserved(self, url: str) -> None:
        item = NewsItem(id="i", title="t", url=url)
        assert item.url == url

    def test_neutralized_on_cache_read(self) -> None:
        # Cache entries are revalidated with model_validate; a poisoned cached
        # item must be sanitized on the way out too.
        item = NewsItem.model_validate(
            {"id": "i", "title": "t", "url": "javascript:evil"}
        )
        assert item.url == ""
