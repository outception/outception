"""Active tropical storms from the hurricane center's keyless feed,
Atlantic and Pacific, strongest first. An empty feed is a real answer:
the card then carries no tiles and hides itself."""

from typing import Any

from outception.redis import Redis

from ...specs import HeatmapSpec
from .. import http

FEED_URL = "https://www.nhc.noaa.gov/CurrentStorms.json"
HOME_URL = "https://www.nhc.noaa.gov/"


def tiles_from(payload: dict[str, Any]) -> list[dict[str, Any]]:
    tiles: list[dict[str, Any]] = []
    for storm in payload.get("activeStorms") or []:
        name = str(storm.get("name") or "").strip()
        classification = str(storm.get("classification") or "").strip()
        wind = storm.get("intensity")
        if not name:
            continue
        try:
            knots = float(wind) if wind not in (None, "") else 0.0
        except TypeError, ValueError:
            knots = 0.0
        pressure = storm.get("pressure")
        direction = str(storm.get("movementDir") or "").strip()
        speed = storm.get("movementSpeed")
        movement = f"{direction} at {speed} kt" if direction and speed else "stationary"
        tiles.append(
            {
                "symbol": name[:14],
                "name": classification or name,
                "changePercent": round(-min(3.0, knots / 40.0), 2),
                "price": knots,
                "weight": max(knots, 1.0),
                "label": movement,
                "subtitle": f"{pressure} mb" if pressure else None,
                "url": HOME_URL,
            }
        )
    tiles.sort(key=lambda tile: -tile["price"])
    return tiles


async def fetch_tiles(redis: Redis, spec: HeatmapSpec) -> list[dict[str, Any]]:
    return tiles_from(await http.fetch_json(FEED_URL))
