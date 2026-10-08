"""Upcoming orbital launches over the next two weeks from the launch
library, soonest first. The free tier allows fifteen calls an hour per
address, so the poll stays at fifteen minutes."""

from datetime import UTC, datetime, timedelta
from typing import Any

from outception.config import settings
from outception.redis import Redis

from ...specs import HeatmapSpec
from .. import http
from ._time import countdown_label, now_ms, parse_iso

FEED_URL = "https://ll.thespacedevs.com/2.2.0/launch/upcoming/"
WINDOW_DAYS = 14
LIMIT = 20
PAGE_URL = "https://spacelaunchnow.me/launch/{slug}"


def tiles_from(
    payload: dict[str, Any], *, now: int | None = None
) -> list[dict[str, Any]]:
    now = now_ms() if now is None else now
    tiles: list[dict[str, Any]] = []
    for launch in payload.get("results") or []:
        name = str(launch.get("name") or "").strip()
        net = parse_iso(launch.get("net"))
        if not name or net is None:
            continue
        rocket, _, mission = name.partition(" | ")
        provider = str((launch.get("launch_service_provider") or {}).get("name") or "")
        status = launch.get("status") or {}
        pad = launch.get("pad") or {}
        location = str((pad.get("location") or {}).get("name") or "")
        slug = str(launch.get("slug") or "")
        net_ms = int(net.timestamp() * 1000)
        tiles.append(
            {
                "symbol": (mission or rocket)[:14],
                "name": f"{rocket} · {provider}" if provider else rocket,
                "changePercent": 3.0
                if str(status.get("abbrev") or "") == "Go"
                else 0.0,
                "price": round(max(0.0, (net_ms - now) / 3_600_000), 1),
                "weight": 1.0,
                "label": countdown_label(net_ms, now),
                "subtitle": " · ".join(
                    part for part in (str(status.get("name") or ""), location) if part
                )
                or None,
                "url": PAGE_URL.format(slug=slug) if slug else None,
                "_net": net_ms,
            }
        )
    tiles.sort(key=lambda tile: tile["_net"])
    for tile in tiles:
        del tile["_net"]
    return tiles[:LIMIT]


async def fetch_tiles(redis: Redis, spec: HeatmapSpec) -> list[dict[str, Any]]:
    start = datetime.now(UTC)
    params = {
        "limit": LIMIT,
        "ordering": "net",
        "net__gte": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "net__lte": (start + timedelta(days=WINDOW_DAYS)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
    }
    headers = (
        {"Authorization": f"Token {settings.LAUNCH_LIBRARY_TOKEN}"}
        if settings.LAUNCH_LIBRARY_TOKEN
        else None
    )
    return tiles_from(await http.fetch_json(FEED_URL, params=params, headers=headers))
