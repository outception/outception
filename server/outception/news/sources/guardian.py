"""The Guardian — World News RSS feed."""

from ..fetch import NewsFetchError, fetch_text, parse_rss
from ..registry import source
from ..schemas import NewsItem

_URL = "https://www.theguardian.com/world/rss"


@source("guardian")
async def guardian() -> list[NewsItem]:
    items = parse_rss(await fetch_text(_URL))
    if not items:
        raise NewsFetchError("Cannot fetch rss data")
    return items
