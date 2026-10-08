"""Most-played games by live player count, with yesterday's counts rotated through Redis so colour is the change since yesterday."""

import json
import re
from typing import Any

from outception.redis import Redis

from ...cache import now_ms
from ..specs import HeatmapSpec
from . import http

_STATS_URL = "https://store.steampowered.com/stats/stats/"
_PREV_KEY = "news:heatmap:steam:prev"
_PREV_DATE_KEY = "news:heatmap:steam:prev-date"


async def fetch_tiles(redis: Redis, spec: HeatmapSpec) -> list[dict[str, Any]]:
    """Most-played Steam games by live player count. Duplicates the small
    stats-page parse from sources/steam.py deliberately: importing that module
    here would cycle metadata → heatmap → sources → registry → metadata.
    Yesterday's counts rotate through Redis so color = change since yesterday
    (0 on the first ever fetch)."""
    soup = await http.fetch_html(_STATS_URL)
    current: dict[str, tuple[str, int]] = {}
    for el in soup.select("#detailStats tr.player_count_row"):
        link = el.select_one("a.gameLink")
        players_el = el.select_one("td:first-child .currentServers")
        if link is None or players_el is None:
            continue
        url = str(link.get("href") or "")
        name = link.get_text(strip=True)
        try:
            players = int(players_el.get_text(strip=True).replace(",", ""))
        except ValueError:
            continue
        if url and name and players > 0:
            current[url] = (name, players)
    if not current:
        return []

    today = str(now_ms() // 86_400_000)  # UTC day ordinal
    prev_date = await redis.get(_PREV_DATE_KEY)
    prev_raw = await redis.get(_PREV_KEY)
    prev: dict[str, int] = {}
    if prev_raw is not None:
        try:
            prev = {k: int(v) for k, v in json.loads(prev_raw).items()}
        except ValueError, TypeError, AttributeError:
            prev = {}
    prev_str = prev_date.decode() if isinstance(prev_date, bytes) else prev_date
    if prev_str != today:
        # New UTC day: today's counts become tomorrow's baseline.
        await redis.set(
            _PREV_KEY,
            json.dumps({url: players for url, (_, players) in current.items()}),
            ex=3 * 86_400,
        )
        await redis.set(_PREV_DATE_KEY, today, ex=3 * 86_400)

    tiles: list[dict[str, Any]] = []
    for url, (name, players) in list(current.items())[:24]:
        baseline = prev.get(url)
        change = (players / baseline - 1.0) * 100.0 if baseline and prev_str else 0.0
        # Store links carry the appid, and Steam's CDN serves capsule art by
        # appid - no extra request needed.
        app_match = re.search(r"/app/(\d+)", url)
        logo = (
            f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_match.group(1)}/capsule_184x69.jpg"
            if app_match
            else None
        )
        tiles.append(
            {
                "symbol": name if len(name) <= 14 else f"{name[:13]}…",
                "name": name,
                "logo": logo,
                "changePercent": round(change, 2),
                "price": float(players),
                "weight": float(players),
                "url": url,
            }
        )
    return tiles
