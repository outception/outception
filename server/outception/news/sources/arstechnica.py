"""Ars Technica — RSS feed."""

from ..fetch import NewsFetchError, fetch_text, parse_rss
from ..registry import source
from ..schemas import NewsItem


@source("arstechnica")
async def arstechnica() -> list[NewsItem]:
    items = parse_rss(
        await fetch_text("https://feeds.arstechnica.com/arstechnica/index")
    )
    if not items:
        raise NewsFetchError("Cannot fetch rss data")
    return items
