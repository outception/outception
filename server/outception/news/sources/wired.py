"""Wired — RSS feed."""

from ..fetch import NewsFetchError, fetch_text, parse_rss
from ..registry import source
from ..schemas import NewsItem

_URL = "https://www.wired.com/feed/rss"


@source("wired")
async def wired() -> list[NewsItem]:
    items = parse_rss(await fetch_text(_URL))
    if not items:
        raise NewsFetchError("Cannot fetch rss data")
    return items
