"""Science, academia and coding feeds - one Google News search getter per
topic (fields, coding, universities).

Feed data lives in ``news.science_data`` so both this module and ``metadata``
can import it without a circular dependency.
"""

from urllib.parse import quote

import feedparser

from ..fetch import NewsFetchError, fetch_text, parse_rss_async
from ..registry import register
from ..schemas import NewsItem
from ..science_data import SCIENCE_FEEDS


def _make_science_getter(query: str, source_id: str) -> None:
    _url = (
        "https://news.google.com/rss/search?q="
        f"{quote(query, safe='+')}&hl=en-US&gl=US&ceid=US:en"
    )

    async def _getter() -> list[NewsItem]:
        text = await fetch_text(_url)
        items = await parse_rss_async(text)
        if not items:
            # A well-formed feed with zero entries is an honest answer for a
            # niche topic; only a non-feed response is a fetch failure.
            if feedparser.parse(text).version:
                return []
            raise NewsFetchError(f"Cannot fetch science RSS for {source_id}")
        return items

    register(source_id, _getter)


for _query, _source_id, _name, _kicker, _column, _logo in SCIENCE_FEEDS:
    _make_science_getter(_query, _source_id)
