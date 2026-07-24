"""NWS Alerts — active watches, warnings, and advisories (Atom feed)."""

from ..fetch import fetch_text, parse_rss
from ..registry import source
from ..schemas import NewsItem

_URL = "https://api.weather.gov/alerts/active.atom"


@source("nwsalerts")
async def nwsalerts() -> list[NewsItem]:
    return parse_rss(await fetch_text(_URL))
