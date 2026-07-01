"""Top Stories via RSS — one source per country (~120 countries), Google News
topic headlines (8 topics), city-level local news (77 cities), and
search-term feeds (49 queries).

Country URL pattern: https://news.google.com/rss?gl={CC}&hl={hl}&ceid={CC}:{hl}
Topic URL pattern:   https://news.google.com/rss/headlines/section/topic/{TOPIC}?hl=en-US&gl=US&ceid=US:en
City URL pattern:    https://news.google.com/rss/headlines/section/geo/{slug}?hl={hl}&gl={gl}&ceid={gl}:{hl}
Search URL pattern:  https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en

All four tables live in ``metadata`` (not here) to avoid a circular import:
registry -> metadata -> sources.gnews -> registry.
This module imports all four tables from metadata and registers one getter
per entry at import time, mirroring the pattern used by reddit.py.

``_COUNTRIES``, ``_TOPICS``, ``_CITIES``, and ``_SEARCHES`` are re-exported
here as aliases so tests can import them from either location.
"""

from ..fetch import NewsFetchError, fetch_text, parse_rss
from ..metadata import (
    GNEWS_CAT_SEARCHES,
    GNEWS_CITIES,
    GNEWS_COUNTRIES,
    GNEWS_SEARCHES,
    GNEWS_TOPICS,
)
from ..registry import register
from ..schemas import NewsItem

# Public aliases for test and external use.
_COUNTRIES = GNEWS_COUNTRIES
_TOPICS = GNEWS_TOPICS
_CITIES = GNEWS_CITIES
_SEARCHES = GNEWS_SEARCHES


def _make_getter(cc: str, hl: str) -> None:
    """Register a top-stories getter for country code *cc*.

    Captures ``cc`` and ``hl`` as parameters so the closure is bound
    correctly even when called in a loop (mirrors reddit.py).
    """
    _url = f"https://news.google.com/rss?gl={cc}&hl={hl}&ceid={cc}:{hl}"
    _source_id = f"gnews-{cc.lower()}"

    async def _getter() -> list[NewsItem]:
        items = parse_rss(await fetch_text(_url))
        if not items:
            raise NewsFetchError(f"Cannot fetch top-stories RSS for country {cc}")
        return items

    register(_source_id, _getter)


def _make_topic_getter(topic: str, source_id: str) -> None:
    """Register a topic-headlines getter for *topic* under *source_id*.

    Captures ``topic`` and ``source_id`` as parameters so the closure is
    bound correctly even when called in a loop.
    """
    _url = (
        f"https://news.google.com/rss/headlines/section/topic/{topic}"
        "?hl=en-US&gl=US&ceid=US:en"
    )

    async def _getter() -> list[NewsItem]:
        items = parse_rss(await fetch_text(_url))
        if not items:
            raise NewsFetchError(f"Cannot fetch topic RSS for {topic}")
        return items

    register(source_id, _getter)


def _make_city_getter(slug: str, source_id: str, hl: str, gl: str) -> None:
    """Register a local-news getter for *slug* (URL-encoded city name) under *source_id*.

    Captures ``slug``, ``source_id``, ``hl``, and ``gl`` by value so the
    closure is bound correctly even when called in a loop.
    """
    _url = (
        f"https://news.google.com/rss/headlines/section/geo/{slug}"
        f"?hl={hl}&gl={gl}&ceid={gl}:{hl}"
    )

    async def _getter() -> list[NewsItem]:
        items = parse_rss(await fetch_text(_url))
        if not items:
            raise NewsFetchError(f"Cannot fetch city RSS for {slug}")
        return items

    register(source_id, _getter)


def _make_search_getter(query: str, source_id: str) -> None:
    """Register a search-term getter for *query* under *source_id*.

    Captures ``query`` and ``source_id`` as parameters so the closure is
    bound correctly even when called in a loop.
    """
    _url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

    async def _getter() -> list[NewsItem]:
        items = parse_rss(await fetch_text(_url))
        if not items:
            raise NewsFetchError(f"Cannot fetch search RSS for {query}")
        return items

    register(source_id, _getter)


for _cc, _hl, _name in _COUNTRIES:
    _make_getter(_cc, _hl)

for _topic, _source_id, _label in _TOPICS:
    _make_topic_getter(_topic, _source_id)

for _slug, _source_id, _display, _hl, _gl in _CITIES:
    _make_city_getter(_slug, _source_id, _hl, _gl)

for _query, _source_id, _display in _SEARCHES:
    _make_search_getter(_query, _source_id)

# Category-tagged searches (pad thin categories).
for _q, _i, _d, _c in GNEWS_CAT_SEARCHES:
    _make_search_getter(_q, _i)
