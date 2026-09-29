"""TechCrunch - RSS feed."""

from ..fetch import NewsFetchError, fetch_text, parse_rss_async
from ..registry import source
from ..schemas import NewsItem


@source("techcrunch")
async def techcrunch() -> list[NewsItem]:
    items = await parse_rss_async(await fetch_text("https://techcrunch.com/feed/"))
    if not items:
        raise NewsFetchError("Cannot fetch rss data")
    return items
