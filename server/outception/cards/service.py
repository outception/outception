"""The envelope for every kind of card, built once here and nowhere
else. The legacy views come from the same objects through `views`."""

import json
import time
from pathlib import Path
from typing import Any

from outception.exceptions import ResourceNotFound
from outception.net import state as signal_state
from outception.net.state import SignalState
from outception.news import cache as news_cache
from outception.news import heatmap, weather
from outception.news.briefing import service as briefing_service
from outception.news.catalog import registry as catalog_registry
from outception.news.clusters.service import cluster_for_urls
from outception.news.endpoints import _get_source
from outception.news.schemas import HeatmapTile, WeatherResponse
from outception.redis import Redis

from .kinds import WEATHER_STRIP_ID, CardKind, briefing_profile, kind_for_type
from .schemas import (
    BriefingPayload,
    Card,
    CardItem,
    FeedPayload,
    StripPayload,
    TablePayload,
)

CITIES_FILE = Path(__file__).resolve().parent.parent / "news" / "data" / "cities.json"
EMPTY_SINCE_KEY = "news:empty-since:{id}"
# A strip is hidden when its reading is older than this.
STRIP_STALE_MS = 3 * 3600 * 1000


def _cities() -> dict[str, tuple[float, float]]:
    try:
        raw = json.loads(CITIES_FILE.read_text())
    except OSError, ValueError:
        return {}
    return {str(k): (float(v[0]), float(v[1])) for k, v in raw.items()}


CITIES = _cities()


async def _feed_state(
    redis: Redis, source_id: str, updated_ms: int, *, now: float | None = None
) -> SignalState:
    """The state of a feed card from what the fetch path recorded: age
    against the interval and TTL, the failure record, and the empty
    marker that says a source has served nothing for a day."""
    now = time.time() if now is None else now
    age_ms = int(now * 1000) - updated_ms
    failure = await signal_state.read_failure(redis, source_id)
    state = signal_state.derive(
        age_ms=age_ms,
        interval_ms=catalog_registry().interval_ms(source_id),
        ttl_ms=news_cache.TTL_MS,
        failure=failure,
        now=now,
    )
    empty_since = await redis.get(EMPTY_SINCE_KEY.format(id=source_id))
    if empty_since is not None:
        try:
            if (
                int(now * 1000) - int(empty_since)
                >= signal_state.FALLBACK_AFTER_SECONDS * 1000
            ):
                return SignalState.fallback
        except TypeError, ValueError:
            pass
    return state


async def feed_card(
    redis: Redis, source_id: str, *, latest: bool = False, client: str | None = None
) -> Card:
    response = await _get_source(redis, source_id, latest=latest, client=client)
    clusters = await cluster_for_urls(
        redis, [item.url for item in response.items if item.url]
    )
    items = []
    for item in response.items:
        found = clusters.get(item.url)
        items.append(
            CardItem.model_validate(
                {
                    **item.model_dump(by_alias=True),
                    "clusterId": found[0] if found else None,
                    "publisherCount": found[1] if found else None,
                }
            )
        )
    return Card(
        id=response.id,
        kind=CardKind.feed,
        meta=catalog_registry().by_id.get(response.id),
        state=await _feed_state(redis, response.id, response.updated_time),
        updated_at=response.updated_time,
        payload=FeedPayload(items=items),
    )


async def table_card(redis: Redis, table_id: str) -> Card:
    result = await heatmap.get_heatmap(redis, table_id)
    failure = await signal_state.read_failure(redis, table_id)
    spec = heatmap.HEATMAPS[table_id]
    age_ms = news_cache.now_ms() - int(result["updatedTime"])
    state = signal_state.derive(
        age_ms=age_ms,
        interval_ms=spec.interval_ms,
        ttl_ms=heatmap.specs.HARD_TTL_SECONDS * 1000,
        failure=failure,
    )
    return Card(
        id=table_id,
        kind=CardKind.table,
        meta=catalog_registry().by_id.get(table_id),
        state=state,
        updated_at=int(result["updatedTime"]),
        payload=TablePayload(
            tiles=[HeatmapTile.model_validate(tile) for tile in result["tiles"]]
        ),
    )


async def briefing_card(redis: Redis, card_id: str) -> Card:
    profile_id = briefing_profile(card_id)
    profile = briefing_service.get_profile(profile_id or "")
    if profile is None:
        raise ResourceNotFound(f"Unknown card: {card_id}")
    briefing = await briefing_service.latest(redis, profile)
    if briefing is None:
        raise ResourceNotFound(f"No briefing built yet for {profile.id}")
    return Card(
        id=card_id,
        kind=CardKind.briefing,
        meta=None,
        state=SignalState.nominal
        if briefing.status == "success"
        else SignalState.stale,
        updated_at=briefing.built_at,
        payload=BriefingPayload(
            profile=profile.id,
            built_at=briefing.built_at,
            stale_after_ms=briefing.stale_after_ms,
            items=briefing.items,
        ),
    )


def strip_location(
    attached_to: str | None, country: str | None
) -> tuple[float | None, float | None, str | None]:
    """Where a weather strip reads: a city card's coordinates when known,
    else the country's capital through the weather resolver."""
    if attached_to and attached_to in CITIES:
        lat, lon = CITIES[attached_to]
        return lat, lon, country
    if attached_to and attached_to.startswith("gnews-") and len(attached_to) == 8:
        return None, None, attached_to[-2:].upper()
    return None, None, country


async def strip_card(
    redis: Redis, *, attached_to: str | None, country: str | None, client: str | None
) -> Card:
    lat, lon, cc = strip_location(attached_to, country)
    reading = await weather.get_weather(redis, lat, lon, cc, client)
    now_ms = news_cache.now_ms()
    return Card(
        id=WEATHER_STRIP_ID,
        kind=CardKind.strip,
        meta=None,
        state=SignalState.nominal,
        updated_at=now_ms,
        payload=StripPayload(
            attached_to=attached_to or (f"gnews-{cc.lower()}" if cc else "weather"),
            weather=WeatherResponse.model_validate(reading),
        ),
    )


async def card_for(
    redis: Redis,
    card_id: str,
    *,
    country: str | None = None,
    attached_to: str | None = None,
    latest: bool = False,
    client: str | None = None,
) -> Card:
    if briefing_profile(card_id) is not None:
        return await briefing_card(redis, card_id)
    if card_id == WEATHER_STRIP_ID:
        return await strip_card(
            redis, attached_to=attached_to, country=country, client=client
        )
    registry = catalog_registry()
    resolved = registry.resolve_known(card_id)
    if resolved is None:
        raise ResourceNotFound(f"Unknown card: {card_id}")
    row = registry.rows[resolved]
    if kind_for_type(row.type) == CardKind.table:
        return await table_card(redis, resolved)
    return await feed_card(redis, resolved, latest=latest, client=client)


def cache_headers(card: Card) -> dict[str, str]:
    """Per-kind cache headers, as the legacy routes send them."""
    if card.kind == CardKind.table:
        return {"Cache-Control": "public, max-age=60, s-maxage=300", "Vary": "Origin"}
    if card.kind == CardKind.strip:
        return {
            "Cache-Control": "public, max-age=300, s-maxage=900, stale-while-revalidate=3600",
            "Vary": "Origin, CF-IPCountry",
        }
    if card.kind == CardKind.briefing:
        return {"Cache-Control": "public, max-age=60, s-maxage=300", "Vary": "Origin"}
    return {"Cache-Control": "private, no-store"}


def as_json(card: Card) -> dict[str, Any]:
    return card.model_dump(by_alias=True, mode="json")
