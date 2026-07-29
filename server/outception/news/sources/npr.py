"""NPR News — RSS feed."""

from ..fetch import NewsFetchError, fetch_text, parse_rss
from ..registry import source
from ..schemas import NewsItem


@source("npr")
async def npr() -> list[NewsItem]:
    items = parse_rss(await fetch_text("https://feeds.npr.org/1001/rss.xml"))
    if not items:
        raise NewsFetchError("Cannot fetch rss data")
    return items
