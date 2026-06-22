"""Product Hunt — RSS feed.

The upstream source preferred the GraphQL API when a private API token
was configured, falling back to the public RSS feed otherwise. We have
no token, so we always serve the public feed.
"""

from ..fetch import NewsFetchError, fetch_text, parse_rss
from ..registry import source
from ..schemas import NewsItem


@source("producthunt")
async def producthunt() -> list[NewsItem]:
    items = parse_rss(await fetch_text("https://www.producthunt.com/feed"))
    if not items:
        raise NewsFetchError("Cannot fetch rss data")
    return items
