"""Shopping-vertical feeds - deals, property, cars, travel-deal getters.

Feed data lives in ``news.shopping_data`` so both this module and ``metadata``
can import it without a circular dependency. Both families are plain URL
feeds (direct RSS or pre-built Google News search URLs), so one factory
covers them.
"""

import time

import feedparser

from ..fetch import NewsFetchError, fetch_text, parse_rss_async
from ..metadata import (
    COUNTRY_CARD_SEARCHES,
    EVENTS_SEARCHES,
    SHOPPING_FALLBACK_SEARCHES,
)
from ..registry import register
from ..schemas import NewsItem
from ..shopping_data import (
    BRAND_DEAL_SEARCHES,
    SHOPPING_FEEDS,
    SHOPPING_SEARCHES,
)

# A deal from months ago is noise, not news - some community feeds (Pepper
# "hot", coupon blogs) resurface old posts. Cap item age per vertical; items
# without a pub date pass through, and if the cap would leave the card nearly
# empty, fall back to the newest items so the card never goes blank.
_MAX_AGE_MS = {"deals": 14 * 86_400_000}
_DEFAULT_MAX_AGE_MS = 60 * 86_400_000
_MIN_ITEMS = 3
_HARD_MAX_AGE_MS = 60 * 86_400_000


def _make_shopping_getter(url: str, source_id: str, column: str) -> None:
    max_age = _MAX_AGE_MS.get(column, _DEFAULT_MAX_AGE_MS)

    async def _getter() -> list[NewsItem]:
        text = await fetch_text(url)
        items = await parse_rss_async(text)
        if not items:
            # A well-formed feed with zero entries is an honest answer (a
            # niche country search can have no stories today) - only a
            # response that isn't a feed at all (block/consent page) is a
            # fetch failure. The distinction keeps the buzz warmer's
            # circuit breaker for real upstream trouble.
            if feedparser.parse(text).version:
                return []
            raise NewsFetchError(f"Cannot fetch shopping RSS for {source_id}")
        cutoff = time.time() * 1000 - max_age
        fresh = [i for i in items if i.pub_date is None or i.pub_date >= cutoff]
        if len(fresh) >= _MIN_ITEMS:
            return fresh
        dated = sorted(items, key=lambda i: i.pub_date or 0, reverse=True)
        return dated[:5]

    register(source_id, _getter)


for _sid, _url, _name, _column, _home in SHOPPING_FEEDS:
    _make_shopping_getter(_url, _sid, _column)

for _sid, _url, _name, _kicker, _column in SHOPPING_SEARCHES:
    _make_shopping_getter(_url, _sid, _column)

for _sid, _url, _name, _kicker, _column in SHOPPING_FALLBACK_SEARCHES:
    _make_shopping_getter(_url, _sid, _column)

for _sid, _url, _name, _kicker, _column in BRAND_DEAL_SEARCHES:
    _make_shopping_getter(_url, _sid, _column)

for _sid, _url, _name, _kicker, _column in EVENTS_SEARCHES:
    _make_shopping_getter(_url, _sid, _column)

for _sid, _url, _name, _kicker, _column, _glyph in COUNTRY_CARD_SEARCHES:
    _make_shopping_getter(_url, _sid, _column)
