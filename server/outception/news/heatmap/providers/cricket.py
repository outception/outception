"""Live and recent matches as an equal-tile grid. The free tier allows a hundred calls a day; the shared cache keeps us far under it."""

from typing import Any
from urllib.parse import quote_plus

from outception.config import settings
from outception.redis import Redis

from ..specs import HeatmapSpec
from . import http

_MATCHES_URL = "https://api.cricapi.com/v1/currentMatches"


async def fetch_tiles(redis: Redis, spec: HeatmapSpec) -> list[dict[str, Any]]:
    """Live and recent cricket matches as an equal-tile grid: a live game burns
    full green, a finished one sits faintly green with its result, an upcoming
    one faintly red with its start status. cricketdata.org free tier is
    100 req/day - the shared 5-minute cache keeps us far under it."""
    payload = await http.fetch_json(
        _MATCHES_URL,
        params={"apikey": settings.CRICKETDATA_API_KEY or "", "offset": 0},
    )
    tiles: list[dict[str, Any]] = []
    for match in (payload.get("data") or [])[:16]:
        teams = match.get("teamInfo") or []
        shorts = [str(t.get("shortname") or "")[:4] for t in teams[:2]]
        if len(shorts) < 2 or not all(shorts):
            names = match.get("teams") or []
            shorts = [str(n)[:3].upper() for n in names[:2]]
        if len(shorts) < 2:
            continue
        started = bool(match.get("matchStarted"))
        ended = bool(match.get("matchEnded"))
        heat = 3.0 if started and not ended else 0.5 if ended else -0.5
        status = str(match.get("status") or "")
        match_name = str(match.get("name") or "")
        tiles.append(
            {
                "symbol": f"{shorts[0]} v {shorts[1]}",
                "name": match_name,
                "changePercent": heat,
                "price": 0.0,
                "weight": 1.0,
                "label": status if len(status) <= 26 else f"{status[:25]}…",
                "url": f"https://news.google.com/search?q={quote_plus(match_name)}"
                if match_name
                else None,
            }
        )
    return tiles
