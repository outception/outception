"""Earthquakes of the last day from the survey's keyless summary feed:
magnitude 2.5 and above, biggest first, thirty at most."""

from typing import Any

from outception.redis import Redis

from ...specs import HeatmapSpec
from .. import http
from ._time import age_label, now_ms

FEED_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson"
MIN_MAGNITUDE = 2.5
LIMIT = 30


def tiles_from(
    payload: dict[str, Any], *, now: int | None = None
) -> list[dict[str, Any]]:
    now = now_ms() if now is None else now
    tiles: list[dict[str, Any]] = []
    for feature in payload.get("features") or []:
        props = feature.get("properties") or {}
        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates") or []
        magnitude = props.get("mag")
        place = str(props.get("place") or "").strip()
        when = props.get("time")
        if not isinstance(magnitude, int | float) or magnitude < MIN_MAGNITUDE:
            continue
        if not place or not isinstance(when, int):
            continue
        depth = coordinates[2] if len(coordinates) > 2 else None
        tiles.append(
            {
                "symbol": f"M{magnitude:.1f}",
                "name": place,
                "changePercent": round(
                    -min(3.0, max(0.0, magnitude - MIN_MAGNITUDE)), 2
                ),
                "price": round(float(magnitude), 1),
                "weight": float(magnitude) ** 2,
                "label": age_label(int(when), now),
                "subtitle": f"{float(depth):.0f} km deep"
                if isinstance(depth, int | float)
                else None,
                "url": str(props.get("url") or "") or None,
            }
        )
    tiles.sort(key=lambda tile: (-tile["price"], tile["name"]))
    return tiles[:LIMIT]


async def fetch_tiles(redis: Redis, spec: HeatmapSpec) -> list[dict[str, Any]]:
    return tiles_from(await http.fetch_json(FEED_URL))
