"""The feed adapters: one factory per family over the shared parser.

- `rss`: a publisher's own feed; raises on an empty answer and treats a feed
  whose newest item is older than the cutoff as abandoned, so a feed the
  publisher stopped posting to never re-caches years-old headlines.
- `rss_lenient`: a feed where empty is a real answer (alerts).
- `gnews`: an aggregator feed (country, topic, city or search); empty is a
  fetch failure.
- `search`: a topic search where a well-formed empty feed is an honest answer
  for a niche topic; only a non-feed response is a failure.
- `shopping`: a deals or property feed with an age cap per vertical, falling
  back to the newest items so the card never goes blank.
"""

import asyncio
import time

import feedparser

from ..fetch import NewsFetchError, StaleFeedError, fetch_text, parse_rss_async
from ..registry import Getter
from ..schemas import NewsItem

_MAX_FEED_AGE_DAYS = 60
_SHOPPING_MIN_ITEMS = 3
_SHOPPING_FALLBACK = 5


def _abandoned(items: list[NewsItem]) -> bool:
    """Whether every dated item predates the staleness cutoff. Undated feeds
    are left alone; the absence of dates says nothing about freshness."""
    dated = [item.pub_date for item in items if item.pub_date]
    if not dated:
        return False
    return max(dated) < (time.time() - _MAX_FEED_AGE_DAYS * 86400) * 1000


def rss(source_id: str, url: str) -> Getter:
    async def getter():  # type: ignore[no-untyped-def]
        items = await parse_rss_async(await fetch_text(url))
        if not items:
            raise NewsFetchError(f"Cannot fetch rss data for {source_id}")
        if _abandoned(items):
            raise StaleFeedError(
                f"{source_id} has published nothing in {_MAX_FEED_AGE_DAYS} days"
            )
        return items

    return getter


def rss_lenient(source_id: str, url: str) -> Getter:
    async def getter():  # type: ignore[no-untyped-def]
        return await parse_rss_async(await fetch_text(url))

    return getter


def gnews(source_id: str, url: str) -> Getter:
    async def getter():  # type: ignore[no-untyped-def]
        items = await parse_rss_async(await fetch_text(url))
        if not items:
            raise NewsFetchError(f"Cannot fetch RSS for {source_id}")
        return items

    return getter


def search(source_id: str, url: str) -> Getter:
    async def getter():  # type: ignore[no-untyped-def]
        text = await fetch_text(url)
        items = await parse_rss_async(text)
        if not items:
            if (await asyncio.to_thread(feedparser.parse, text)).version:
                return []
            raise NewsFetchError(f"Cannot fetch search RSS for {source_id}")
        return items

    return getter


def shopping(source_id: str, url: str, max_age_days: int) -> Getter:
    max_age_ms = max_age_days * 86_400_000

    async def getter():  # type: ignore[no-untyped-def]
        text = await fetch_text(url)
        items = await parse_rss_async(text)
        if not items:
            if (await asyncio.to_thread(feedparser.parse, text)).version:
                return []
            raise NewsFetchError(f"Cannot fetch shopping RSS for {source_id}")
        cutoff = time.time() * 1000 - max_age_ms
        fresh = [i for i in items if i.pub_date is None or i.pub_date >= cutoff]
        if len(fresh) >= _SHOPPING_MIN_ITEMS:
            return fresh
        dated = sorted(items, key=lambda i: i.pub_date or 0, reverse=True)
        return dated[:_SHOPPING_FALLBACK]

    return getter
