"""The Verge — RSS feed."""

from ..fetch import NewsFetchError, fetch_text, parse_rss
from ..registry import source
from ..schemas import NewsItem


@source("theverge")
async def theverge() -> list[NewsItem]:
    items = parse_rss(await fetch_text("https://www.theverge.com/rss/index.xml"))
    if not items:
        raise NewsFetchError("Cannot fetch rss data")
    return items
