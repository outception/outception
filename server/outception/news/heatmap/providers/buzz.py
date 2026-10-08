"""News-volume tiles from feeds already cached on the wall: no external calls, area by story count in the last week, colour by how fresh the latest story is."""

import json
from typing import Any
from urllib.parse import quote_plus

from outception.redis import Redis

from ...cache import mget_hot_raw, now_ms
from ..specs import HeatmapSpec

DEMAND_KEY = "news:heatmap:demand:{id}"
DEMAND_TTL_SECONDS = 48 * 60 * 60


_BUZZ_FRESH_MS = 7 * 24 * 60 * 60 * 1000


def buzz_family(spec: HeatmapSpec) -> list[tuple[str, str, str | None]]:
    """(source_id, display name, logo) triples for a buzz map's entity family,
    selected by `spec.code`'s comma-list of source-id prefixes (e.g. city
    feeds). Shared between the tile builder and the background warmer so both
    agree on exactly which feeds constitute a map."""
    # Function-level import ON PURPOSE: metadata imports this module to build
    # the roster, so a top-level import back at metadata would be circular. By
    # the time a request reaches this fetcher both modules are fully loaded.
    from ...registry import SOURCES

    prefixes = tuple(p for p in spec.code.split(",") if p)
    family: list[tuple[str, str, str | None]] = []
    for source_id, meta in SOURCES.items():
        # The "-new" vertical cards (movie-new, tv-new, …) are curated release
        # feeds, not entities - they'd dominate every buzz map as one always-
        # fresh mega-tile.
        if not source_id.startswith(prefixes) or source_id.endswith("-new"):
            continue
        name = str(meta.get("name") or source_id)
        # The per-country Top Stories feeds all share one name; their distinct
        # label (the country) lives in `title` - without this the World Buzz
        # map renders every tile as "Top Stories".
        if name == "Top Stories":
            name = str(meta.get("title") or name)
        logo = str(meta.get("logo") or "") or None
        family.append((source_id, name, logo))
    return family


async def demanded_buzz_ids(redis: Redis) -> list[str]:
    """Buzz map ids someone viewed within the demand window."""
    from ..specs import HEATMAPS

    buzz_ids = [hid for hid, spec in HEATMAPS.items() if spec.provider == "buzz"]
    flags = await redis.mget([DEMAND_KEY.format(id=hid) for hid in buzz_ids])
    return [hid for hid, flag in zip(buzz_ids, flags, strict=True) if flag]


async def fetch_tiles(redis: Redis, spec: HeatmapSpec) -> list[dict[str, Any]]:
    """News-volume tiles from feeds already cached on the wall (no external
    calls): area by story count in the last 7 days, color by how fresh the
    latest story is (older than two days reads faint, not absent)."""
    family = buzz_family(spec)
    if not family:
        return []
    # Chunk the MGETs: the topics family is 500+ ids and one giant MGET would
    # sit on Redis' hot path (search.py uses the same 250 bound).
    ids = [source_id for source_id, _, _ in family]
    raws: list[tuple[str, str | bytes | None]] = []
    for start in range(0, len(ids), 250):
        raws.extend(await mget_hot_raw(redis, ids[start : start + 250]))
    names = {source_id: name for source_id, name, _ in family}
    logos = {source_id: logo for source_id, _, logo in family}
    now = now_ms()
    tiles: list[dict[str, Any]] = []
    for source_id, raw in raws:
        # Read the dates off the raw dicts, never through NewsItem. This loop
        # wants one integer field per item, and the YouTube buzz family alone
        # is 552 sources x 30 items - 16,500 model constructions, ~77 ms of
        # blocking event-loop CPU, to read `pubDate`. The refresh is armed as a
        # task on a serving request's loop, so that stall lands on every other
        # request in the worker. Same reasoning as follows.followed_feed.
        if raw is None:
            continue
        try:
            items = json.loads(raw)["items"]
        except ValueError, KeyError, TypeError:
            continue
        if not isinstance(items, list):
            continue
        dates = [
            date
            for item in items
            if isinstance(item, dict) and isinstance(date := item.get("pubDate"), int)
        ]
        fresh = sum(1 for ms in dates if now - ms < _BUZZ_FRESH_MS)
        if fresh == 0:
            continue
        newest_hours = (now - max(dates)) / 3_600_000 if dates else 999.0
        # Old-but-within-a-week reads neutral (the clients' zero color), not
        # negative - "quiet" isn't "down" on a buzz map.
        heat = (
            3.0
            if newest_hours < 6
            else 1.5
            if newest_hours < 24
            else 0.5
            if newest_hours < 48
            else 0.0
        )
        name = names[source_id]
        short = name
        if spec.strip:
            short = short.removeprefix(spec.strip).strip() or short
        tiles.append(
            {
                "symbol": short[:14],
                "name": name,
                "logo": logos.get(source_id),
                "changePercent": heat,
                "price": float(fresh),
                "weight": float(fresh),
                "label": f"{fresh} " + ("story" if fresh == 1 else "stories"),
                "url": f"https://news.google.com/search?q={quote_plus(name)}",
            }
        )
    # One or two cached feeds is not real coverage of the family - a map built
    # from them is a single mega-tile ("DUBLIN, 9 stories" filling the card).
    # Fail the build instead, so the card drops off the wall until the warmer
    # has the family cached.
    if len(tiles) < 3:
        return []
    tiles.sort(key=lambda tile: tile["weight"], reverse=True)
    return tiles[:28]
