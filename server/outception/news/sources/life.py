"""Lifestyle & interest feeds — one Google News search getter per topic.

Feed data lives in ``news.life_data`` so both this module and ``metadata`` can
import it without a circular dependency.
"""

from urllib.parse import quote

from ..cities_data import CITY_FEEDS
from ..fetch import NewsFetchError, fetch_text, parse_rss_async
from ..life_data import LIFE_FEEDS
from ..music_gaming_data import MUSIC_GAMING_FEEDS
from ..registry import register
from ..schemas import NewsItem


def _make_life_getter(query: str, source_id: str) -> None:
    _url = (
        "https://news.google.com/rss/search?q="
        f"{quote(query, safe='+')}&hl=en-US&gl=US&ceid=US:en"
    )

    async def _getter() -> list[NewsItem]:
        items = await parse_rss_async(await fetch_text(_url))
        if not items:
            raise NewsFetchError(f"Cannot fetch life RSS for {source_id}")
        return items

    register(source_id, _getter)


for _query, _source_id, _name, _kicker, _column in LIFE_FEEDS:
    _make_life_getter(_query, _source_id)

for _query, _source_id, _name, _kicker, _column in MUSIC_GAMING_FEEDS:
    _make_life_getter(_query, _source_id)

for _query, _source_id, _name, _kicker, _column in CITY_FEEDS:
    _make_life_getter(_query, _source_id)
