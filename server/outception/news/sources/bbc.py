"""BBC World News — RSS feed."""

from ..fetch import NewsFetchError, fetch_text, parse_rss_async
from ..registry import register, source
from ..schemas import NewsItem

_URL = "https://feeds.bbci.co.uk/news/world/rss.xml"


@source("bbc-world")
async def bbc_world() -> list[NewsItem]:
    items = await parse_rss_async(await fetch_text(_URL))
    if not items:
        raise NewsFetchError("Cannot fetch rss data")
    return items


register("bbc", bbc_world)
