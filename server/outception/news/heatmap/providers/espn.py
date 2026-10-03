"""Standings, rankings and fight cards from the sports network's keyless public JSON."""

import re
from typing import Any
from urllib.parse import quote_plus

from outception.redis import Redis

from ..specs import HeatmapSpec
from . import http

_STANDINGS_URL = "https://site.api.espn.com/apis/v2/sports"
_SITE_URL = "https://site.api.espn.com/apis/site/v2/sports"
# The edge refuses browser user agents without a browser's TLS fingerprint
# but accepts an honest client, so these fetches identify as what they are.
_HEADERS = {"User-Agent": "python-httpx"}


def _zone_heat(spec: HeatmapSpec, position: int, total: int) -> float:
    """Standings color from the competition's qualification zones (see the
    zone_* spec fields): qualification burns green, the drop zone red, the
    soft bands lighter, mid-table neutral."""
    if position <= spec.zone_green:
        return 3.0
    if position <= spec.zone_green + spec.zone_soft:
        return 1.2
    if position > total - spec.zone_red:
        return -3.0
    if position > total - spec.zone_red - spec.zone_red_soft:
        return -1.2
    return 0.0


def _has_zones(spec: HeatmapSpec) -> bool:
    return bool(spec.zone_green or spec.zone_red)


def _espn_season_note(payload: dict[str, Any], phase: str) -> str:
    """Season stamp for points-table labels, parsed from ESPN's season display
    name - "2026-27" for cross-year leagues, "2026" for calendar leagues like
    the Brasileirão. `phase` is "season" (a reset table) or "final" (last
    season's completed table)."""
    display = str((payload.get("season") or {}).get("displayName") or "")
    match = re.match(r"(\d{4})(?:-(\d{2}))?", display)
    if not match:
        return ""
    if match.group(2):
        return f" · {int(match.group(1)) % 100:02d}/{match.group(2)} {phase}"
    return f" · {match.group(1)} {phase}"


def _espn_groups(payload: dict[str, Any]) -> list[list[dict[str, Any]]]:
    groups: list[list[dict[str, Any]]] = [
        (group.get("standings") or {}).get("entries") or []
        for group in payload.get("children") or []
    ]
    groups = [entries for entries in groups if entries]
    if not groups:
        groups = [(payload.get("standings") or {}).get("entries") or []]
    return groups


def _espn_played_any(groups: list[list[dict[str, Any]]]) -> bool:
    for entries in groups:
        for entry in entries:
            for stat in entry.get("stats") or []:
                if (
                    stat.get("name") == "gamesPlayed"
                    and int(stat.get("value") or 0) > 0
                ):
                    return True
    return False


async def fetch_standings(redis: Redis, spec: HeatmapSpec) -> list[dict[str, Any]]:
    """Big-4 standings as tiles: area by wins (or table points), color by the
    competition's qualification zones when the spec declares them (playoff
    seats green, drop zone red - computed per conference/league group),
    otherwise by the current streak. ESPN's public standings JSON is
    keyless."""
    payload = await http.fetch_json(
        f"{_STANDINGS_URL}/{spec.code}/standings", headers=_HEADERS
    )
    season_note = ""
    # Pre-season honesty, readable edition: an all-zero points table is the
    # NEW season's reset - a wall of "0 pts" tells the reader nothing, so
    # serve LAST season's final table from ESPN's archive, stamped "· 25/26
    # final". If the archive is missing, keep the reset table stamped with
    # the new season instead.
    if spec.table and not _espn_played_any(_espn_groups(payload)):
        year = int((payload.get("season") or {}).get("year") or 0)
        if year:
            try:
                prev = await http.fetch_json(
                    f"{_STANDINGS_URL}/{spec.code}/standings",
                    headers=_HEADERS,
                    params={"season": year - 1},
                )
            except http.NewsFetchError:
                prev = None
            if prev and _espn_played_any(_espn_groups(prev)):
                payload = prev
                season_note = _espn_season_note(prev, "final")
        if not season_note:
            season_note = _espn_season_note(payload, "season")
    groups = _espn_groups(payload)
    tiles: list[dict[str, Any]] = []
    for entries in groups:
        rows: list[dict[str, Any]] = []
        for entry in entries:
            team = entry.get("team") or {}
            name = str(team.get("displayName") or "")
            symbol = str(team.get("abbreviation") or name[:3].upper())
            stats = {
                str(s.get("name")): s for s in entry.get("stats") or [] if s.get("name")
            }
            wins = int((stats.get("wins") or {}).get("value") or 0)
            losses = int((stats.get("losses") or {}).get("value") or 0)
            if not name:
                continue
            # Big-4 standings carry a `streak` (±games); soccer leagues carry
            # `rankChange` (positions climbed) instead - both natural heat.
            if "streak" in stats:
                streak_heat = float((stats.get("streak") or {}).get("value") or 0.0)
            else:
                streak_heat = float((stats.get("rankChange") or {}).get("value") or 0.0)
            # Points-table sports size by points; win-loss sports by wins.
            if spec.table:
                points = int((stats.get("points") or {}).get("value") or 0)
                weight = float(max(points, 1))
                label = f"{points} pts"
                price = float(points)
            else:
                weight = float(wins + 1)
                label = f"{wins}-{losses}"
                price = float(wins)
            links = team.get("links") or []
            url = str(links[0].get("href")) if links and links[0].get("href") else None
            logos = team.get("logos") or []
            logo = str(logos[0].get("href")) if logos and logos[0].get("href") else None
            rows.append(
                {
                    "symbol": symbol,
                    "name": name,
                    "logo": logo,
                    "changePercent": round(max(-3.0, min(streak_heat, 3.0)), 2),
                    "price": price,
                    "weight": weight,
                    "label": label,
                    "url": url,
                    # gamesPlayed where the league provides it (rugby tables
                    # carry no wins/losses stats, which read as 0-0 forever).
                    "_played": int((stats.get("gamesPlayed") or {}).get("value") or 0)
                    or wins + losses,
                }
            )
        # Zones (or streak remnants) only mean something once the season is
        # genuinely underway - until at least half the group has played,
        # standings order is alphabetical accident (one Hall-of-Fame preseason
        # game made "top 7" = ARI/ATL/CHI/DAL/DET/GB), and ESPN keeps last
        # season's streak values on 0-0 rows.
        played_count = sum(1 for row in rows if row["_played"] > 0)
        if season_note:
            for row in rows:
                row["label"] += season_note
        if played_count * 2 < len(rows):
            for row in rows:
                row["changePercent"] = 0.0
        elif _has_zones(spec):
            # Seats within the group follow the sized metric (points/wins) -
            # the same order the treemap ranks the tiles.
            rows.sort(key=lambda row: (-row["weight"], row["name"]))
            for seat, row in enumerate(rows, start=1):
                row["changePercent"] = _zone_heat(spec, seat, len(rows))
        for row in rows:
            del row["_played"]
        tiles.extend(rows)
    return tiles


async def fetch_rankings(redis: Redis, spec: HeatmapSpec) -> list[dict[str, Any]]:
    """Poll/ranking grids (CFB Top 25, ATP/WTA): tiles sized by poll or
    ranking points, colored by places moved since last week, labelled with the
    rank. Works for team polls (`team`) and athlete rankings (`athlete`)."""
    payload = await http.fetch_json(
        f"{_SITE_URL}/{spec.code}/rankings", headers=_HEADERS
    )
    rankings = payload.get("rankings") or []
    ranks = (rankings[0] if rankings else {}).get("ranks") or []
    tiles: list[dict[str, Any]] = []
    for entry in ranks[:25]:
        team = entry.get("team") or {}
        athlete = entry.get("athlete") or {}
        name = str(
            team.get("nickname")
            or team.get("displayName")
            or athlete.get("displayName")
            or ""
        )
        symbol = str(team.get("abbreviation") or athlete.get("shortName") or name[:12])
        if not name:
            continue
        current = int(entry.get("current") or 0)
        points = float(entry.get("points") or 0.0)
        trend_raw = str(entry.get("trend") or "").strip()
        try:
            # "+3" climbed, "-2" dropped, "-" unchanged.
            trend = float(trend_raw)
        except ValueError:
            trend = 0.0
        # Team polls carry a plain `logo` url; athlete rankings a `headshot`
        # (string or {href}).
        headshot = athlete.get("headshot")
        logo = (
            str(team.get("logo") or "")
            or (
                str(headshot.get("href") or "")
                if isinstance(headshot, dict)
                else str(headshot or "")
            )
        ) or None
        tiles.append(
            {
                "symbol": symbol,
                "name": name,
                "logo": logo,
                "changePercent": round(max(-3.0, min(trend, 3.0)), 2),
                "price": float(current),
                "weight": max(points, 1.0),
                "label": f"#{current}",
                "url": f"https://news.google.com/search?q={quote_plus(name)}",
            }
        )
    return tiles


async def fetch_fight_card(redis: Redis, spec: HeatmapSpec) -> list[dict[str, Any]]:
    """The nearest event's fight card as equal tiles: live fights burn green,
    finished ones sit faint with the winner marked, upcoming ones neutral."""
    payload = await http.fetch_json(
        f"{_SITE_URL}/{spec.code}/scoreboard", headers=_HEADERS
    )
    events = payload.get("events") or []
    if not events:
        return []
    event = events[0]
    tiles: list[dict[str, Any]] = []
    for bout in (event.get("competitions") or [])[:16]:
        competitors = bout.get("competitors") or []
        names = [
            str(((c.get("athlete") or {}).get("shortName")) or "")
            for c in competitors[:2]
        ]
        if len(names) < 2 or not all(names):
            continue
        status = bout.get("status") or {}
        state = str((status.get("type") or {}).get("state") or "")
        completed = bool((status.get("type") or {}).get("completed"))
        winner = next(
            (
                str(((c.get("athlete") or {}).get("shortName")) or "")
                for c in competitors
                if c.get("winner")
            ),
            None,
        )
        heat = 3.0 if state == "in" else 0.5 if completed else -0.5
        label = (
            f"{winner} won"
            if winner
            else str((status.get("type") or {}).get("shortDetail") or "")[:26]
        )
        tiles.append(
            {
                "symbol": f"{names[0]} v {names[1]}",
                "name": str(event.get("name") or ""),
                "changePercent": heat,
                "price": 0.0,
                "weight": 1.0,
                "label": label,
                "url": (
                    "https://news.google.com/search?"
                    f"q={quote_plus(f'{names[0]} vs {names[1]}')}"
                ),
            }
        )
    return tiles
