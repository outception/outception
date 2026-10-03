from outception.news.clusters.urlkey import canonical_url, url_key


class TestCanonical:
    def test_tracking_and_mirrors_collapse(self) -> None:
        plain = "https://example.com/news/story-123"
        variants = [
            "https://www.example.com/news/story-123/",
            "http://m.example.com/news/story-123?utm_source=feed&utm_medium=rss",
            "https://amp.example.com/news/story-123/amp",
            "https://example.com/news/story-123#comments",
            "https://example.com/news/story-123?fbclid=abc&ref=home",
            "https://example.com/news/story-123/index.html",
        ]
        for variant in variants:
            assert canonical_url(variant) == plain, variant
            assert url_key(variant) == url_key(plain), variant

    def test_meaningful_params_survive_and_sort(self) -> None:
        assert canonical_url("https://example.com/a?page=2&id=7&utm_term=x") == (
            "https://example.com/a?id=7&page=2"
        )
        assert url_key("https://example.com/a?id=7") != url_key(
            "https://example.com/a?id=8"
        )

    def test_key_shape(self) -> None:
        key = url_key("https://example.com/x")
        assert len(key) == 32
        assert key == url_key("HTTPS://EXAMPLE.COM/x")
