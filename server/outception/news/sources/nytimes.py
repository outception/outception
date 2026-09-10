"""The New York Times - home page RSS feed."""

from ..fetch import NewsFetchError, fetch_text, parse_rss_async
from ..registry import source
from ..schemas import NewsItem


@source("nytimes")
async def nytimes() -> list[NewsItem]:
    items = await parse_rss_async(
        await fetch_text("https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml")
    )
    if not items:
        raise NewsFetchError("Cannot fetch rss data")
    return items
