"""The drivers' championship as tiles: area by season points, colour by how the driver scored in the last race."""

from typing import Any

from outception.redis import Redis

from ..specs import HeatmapSpec
from . import http

_BASE_URL = "https://api.jolpi.ca/ergast/f1"


async def fetch_tiles(redis: Redis, spec: HeatmapSpec) -> list[dict[str, Any]]:
    """Driver championship as tiles: area by season points, color by how the
    driver scored in the LAST race (a winner burns full green, a pointless
    finish reads faintly red), label = the points tally. Jolpica mirrors the
    retired Ergast API, keyless."""
    standings_payload = await http.fetch_json(
        f"{_BASE_URL}/current/driverstandings.json"
    )
    lists = ((standings_payload.get("MRData") or {}).get("StandingsTable") or {}).get(
        "StandingsLists"
    ) or []
    standings = (lists[0] if lists else {}).get("DriverStandings") or []
    last_points: dict[str, float] = {}
    try:
        last_payload = await http.fetch_json(f"{_BASE_URL}/current/last/results.json")
        races = ((last_payload.get("MRData") or {}).get("RaceTable") or {}).get(
            "Races"
        ) or []
        for result in (races[0] if races else {}).get("Results") or []:
            code = str((result.get("Driver") or {}).get("code") or "")
            if code:
                last_points[code] = float(result.get("points") or 0.0)
    except http.NewsFetchError:
        pass  # standings alone still make a map; tiles just read neutral
    tiles: list[dict[str, Any]] = []
    for row in standings:
        driver = row.get("Driver") or {}
        code = str(driver.get("code") or "")
        name = f"{driver.get('givenName', '')} {driver.get('familyName', '')}".strip()
        points = float(row.get("points") or 0.0)
        if not name:
            continue
        scored = last_points.get(code)
        # Clamp to ±3 like every other fetcher - sprint/fastest-lap bonuses can
        # push a single race past 25 points.
        heat = (
            0.0
            if scored is None
            else min((scored / 25.0) * 3.0, 3.0)
            if scored > 0
            else -0.6
        )
        tiles.append(
            {
                "symbol": code or name[:3].upper(),
                "name": name,
                "changePercent": round(heat, 2),
                "price": points,
                "weight": points + 1.0,
                "label": f"{points:g} pts",
                "url": str(driver.get("url")) if driver.get("url") else None,
            }
        )
    return tiles
