"""City search: a typed place resolves to a city card. Known cards match by
normalised name without any network; anything else goes through a keyless
geocoder, is normalised to locality, region and country, and lands on the
nearest city card when one sits within reach. Negative results are cached
briefly so a misspelling does not hammer the geocoder. New city cards are
catalog rows, added by the operator script, never minted at request time."""

import json
import math
import re
import unicodedata
from functools import cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from outception.redis import Redis

from .catalog import registry as catalog_registry
from .fetch import NewsFetchError, fetch_json

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
CACHE_KEY = "news:geocode:{q}"
CACHE_TTL_SECONDS = 3600
NEGATIVE_TTL_SECONDS = 600
# A geocoded place this close to a city card's centre opens that card.
NEAR_KM = 40.0
CITIES_FILE = Path(__file__).resolve().parent / "data" / "cities.json"


class Place(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    admin: str | None = None
    country: str | None = None
    country_code: str | None = Field(default=None, alias="countryCode")
    latitude: float
    longitude: float


class CityResolution(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    query: str
    place: Place | None
    card_id: str | None = Field(alias="cardId")


_SUFFIXES = (" city", " town")


def normalize_toponym(text: str) -> str:
    """Lowercase, accents stripped, punctuation collapsed to spaces, a
    trailing "city" dropped: `São Paulo` and `sao-paulo` meet in the middle."""
    folded = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in folded if not unicodedata.combining(ch))
    collapsed = re.sub(r"[^a-z0-9]+", " ", stripped.lower()).strip()
    for suffix in _SUFFIXES:
        if collapsed.endswith(suffix) and len(collapsed) > len(suffix):
            collapsed = collapsed[: -len(suffix)].strip()
    return collapsed


@cache
def _city_index() -> tuple[tuple[str, str], ...]:
    registry = catalog_registry()
    return tuple(
        (normalize_toponym(row.name or ""), row.id)
        for row in registry.rows.values()
        if row.column == "cities" and not row.redirect and row.name
    )


def match_city_card(query: str) -> str | None:
    """A city card whose name is the query, else the one card whose name
    starts with it; ambiguity returns nothing rather than a guess."""
    q = normalize_toponym(query)
    if not q:
        return None
    for name, card_id in _city_index():
        if name == q:
            return card_id
    prefixed = [card_id for name, card_id in _city_index() if name.startswith(q)]
    return prefixed[0] if len(prefixed) == 1 else None


@cache
def _coordinates() -> dict[str, tuple[float, float]]:
    try:
        raw = json.loads(CITIES_FILE.read_text())
    except OSError, ValueError:
        return {}
    return {str(k): (float(v[0]), float(v[1])) for k, v in raw.items()}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def nearest_city_card(
    latitude: float,
    longitude: float,
    coordinates: dict[str, tuple[float, float]] | None = None,
    *,
    within_km: float = NEAR_KM,
) -> str | None:
    best: tuple[float, str] | None = None
    for card_id, (lat, lon) in (coordinates or _coordinates()).items():
        distance = haversine_km(latitude, longitude, lat, lon)
        if distance <= within_km and (best is None or distance < best[0]):
            best = (distance, card_id)
    return best[1] if best else None


def _place_from(result: dict[str, Any]) -> Place | None:
    try:
        return Place(
            name=str(result["name"]),
            admin=result.get("admin1"),
            country=result.get("country"),
            country_code=result.get("country_code"),
            latitude=float(result["latitude"]),
            longitude=float(result["longitude"]),
        )
    except KeyError, TypeError, ValueError:
        return None


async def geocode(redis: Redis, query: str) -> Place | None:
    """The first place the geocoder returns for the query, cached an hour;
    a miss is remembered ten minutes."""
    key = CACHE_KEY.format(q=normalize_toponym(query))
    cached = await redis.get(key)
    if cached is not None:
        return Place.model_validate_json(cached) if cached else None
    try:
        data = await fetch_json(
            GEOCODE_URL,
            params={"name": query, "count": 5, "language": "en", "format": "json"},
        )
    except NewsFetchError:
        return None
    results = data.get("results") if isinstance(data, dict) else None
    place = _place_from(results[0]) if results else None
    if place is None:
        await redis.set(key, "", ex=NEGATIVE_TTL_SECONDS)
        return None
    await redis.set(key, place.model_dump_json(by_alias=True), ex=CACHE_TTL_SECONDS)
    return place


async def resolve_city(redis: Redis, query: str) -> CityResolution:
    direct = match_city_card(query)
    if direct is not None:
        return CityResolution(query=query, place=None, card_id=direct)
    place = await geocode(redis, query)
    if place is None:
        return CityResolution(query=query, place=None, card_id=None)
    card = match_city_card(place.name) or nearest_city_card(
        place.latitude, place.longitude
    )
    return CityResolution(query=query, place=place, card_id=card)
