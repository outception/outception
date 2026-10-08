"""Large wildfires burning in the United States from the interagency
incident feed, biggest first. Colour inverts with containment: an
uncontained fire burns red, a contained one fades to neutral."""

from typing import Any

from outception.redis import Redis

from ...specs import HeatmapSpec
from .. import http

FEED_URL = (
    "https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services/"
    "WFIGS_Incident_Locations_Current/FeatureServer/0/query"
)
MIN_ACRES = 1000
LIMIT = 30
QUERY = {
    "where": f"IncidentTypeCategory='WF' AND DailyAcres>{MIN_ACRES}",
    "outFields": "IncidentName,DailyAcres,PercentContained,POOState,POOCounty,InciWebUrl",
    "orderByFields": "DailyAcres DESC",
    "resultRecordCount": LIMIT,
    "f": "json",
}


def tiles_from(payload: dict[str, Any]) -> list[dict[str, Any]]:
    tiles: list[dict[str, Any]] = []
    for feature in payload.get("features") or []:
        attrs = feature.get("attributes") or {}
        name = str(attrs.get("IncidentName") or "").strip()
        acres = attrs.get("DailyAcres")
        if not name or not isinstance(acres, int | float) or acres < MIN_ACRES:
            continue
        contained = attrs.get("PercentContained")
        contained = float(contained) if isinstance(contained, int | float) else 0.0
        contained = max(0.0, min(100.0, contained))
        state = str(attrs.get("POOState") or "").replace("US-", "")
        county = str(attrs.get("POOCounty") or "").strip()
        where = ", ".join(
            part for part in (f"{county} County" if county else "", state) if part
        )
        tiles.append(
            {
                "symbol": name[:14],
                "name": f"{name} Fire" if not name.lower().endswith("fire") else name,
                "changePercent": round(-3.0 * (1.0 - contained / 100.0), 2),
                "price": float(acres),
                "weight": float(acres),
                "label": f"{contained:.0f}% contained",
                "subtitle": where or None,
                "url": str(attrs.get("InciWebUrl") or "") or None,
            }
        )
    tiles.sort(key=lambda tile: -tile["price"])
    return tiles[:LIMIT]


async def fetch_tiles(redis: Redis, spec: HeatmapSpec) -> list[dict[str, Any]]:
    return tiles_from(await http.fetch_json(FEED_URL, params=QUERY))
