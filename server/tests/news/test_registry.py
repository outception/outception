import pytest

import polar.news.sources  # noqa: F401 — registers every source getter at import
from polar.news import registry
from polar.news.cache import DEFAULT_INTERVAL_MS
from polar.news.metadata import SOURCES
from polar.news.schemas import NewsItem


def test_resolve_known_source() -> None:
    assert registry.resolve("hackernews") == "hackernews"


def test_resolve_follows_redirect_alias_to_canonical() -> None:
    # `reddit` and `github` are redirect aliases in the metadata.
    assert registry.resolve("reddit") == "reddit-popular"
    assert registry.resolve("github") == "github-trending-today"


def test_resolve_unknown_id_returns_none() -> None:
    assert registry.resolve("definitely-not-a-real-source") is None


def test_resolve_meta_without_getter_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The security boundary: an id present in metadata but with no registered
    # getter must not resolve (no path from user input to an arbitrary fetch).
    monkeypatch.setitem(SOURCES, "phantom-source", {"name": "Phantom"})
    assert registry.resolve("phantom-source") is None


def test_register_adds_getter() -> None:
    async def getter() -> list[NewsItem]:
        return []

    registry.register("unit-test-source", getter)
    try:
        assert registry.GETTERS["unit-test-source"] is getter
    finally:
        registry.GETTERS.pop("unit-test-source", None)


def test_source_decorator_registers() -> None:
    @registry.source("unit-test-decorated")
    async def getter() -> list[NewsItem]:
        return []

    try:
        assert registry.GETTERS["unit-test-decorated"] is getter
    finally:
        registry.GETTERS.pop("unit-test-decorated", None)


def test_interval_ms_falls_back_to_default_for_unknown() -> None:
    assert registry.interval_ms("definitely-not-a-real-source") == DEFAULT_INTERVAL_MS
