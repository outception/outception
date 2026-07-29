"""Sports team & league feeds — one Google News search getter per team.

The feed data (and the per-country map) lives in ``news.teams_data`` so both
this module and ``metadata`` can import it without a circular dependency.
"""

from urllib.parse import quote

from ..fetch import NewsFetchError, fetch_text, parse_rss
from ..registry import register
from ..schemas import NewsItem
from ..teams_data import TEAM_FEEDS


def _make_team_getter(query: str, source_id: str) -> None:
    """Register a Google News search getter for *query* under *source_id*.

    ``query`` and ``source_id`` are bound as parameters so the closure is
    correct when built in a loop.
    """
    _url = (
        "https://news.google.com/rss/search?q="
        f"{quote(query, safe='+')}&hl=en-US&gl=US&ceid=US:en"
    )

    async def _getter() -> list[NewsItem]:
        items = parse_rss(await fetch_text(_url))
        if not items:
            raise NewsFetchError(f"Cannot fetch team RSS for {source_id}")
        return items

    register(source_id, _getter)


for _query, _source_id, _name, _kicker in TEAM_FEEDS:
    _make_team_getter(_query, _source_id)
