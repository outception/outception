"""Redis cache for fetched news items.

Two timescales (ported semantics):
  - per-source ``interval`` (metadata, default 10 min): content fresher
    than this is served as ``status:"success"`` without refetching.
  - global ``TTL`` (3 h): content older than ``interval`` but younger
    than this is served as ``status:"cache"``; beyond it we refetch. The
    window is generous so rate-limited sources warmed on a slow rotation
    stay served from cache between passes.

Redis ``ex=`` is set to the hard TTL so keys self-expire; the softer
``interval`` comparison happens in Python against the stored timestamp.
"""

import json
import time
from dataclasses import dataclass

from outception.redis import Redis

from .schemas import NewsItem

TTL_MS = 180 * 60 * 1000
DEFAULT_INTERVAL_MS = 10 * 60 * 1000

_KEY = "news:source:{id}"
_KEY_SORTED = "news:source:{id}:{sort}"


def cache_key(source_id: str, sort: str = "hot") -> str:
    """Return the Redis key for *source_id* + *sort*.

    The plain (hot / absent) path keeps the original key format so
    existing cached entries are not invalidated by this change.
    """
    if sort == "hot":
        return _KEY.format(id=source_id)
    return _KEY_SORTED.format(id=source_id, sort=sort)


def now_ms() -> int:
    return int(time.time() * 1000)


@dataclass
class CacheEntry:
    updated: int  # epoch ms
    items: list[NewsItem]


def parse_entry(raw: str | bytes | None) -> CacheEntry | None:
    """Deserialize a raw cache payload into a `CacheEntry`. A missing or
    malformed entry is a cache miss (``None``), not an error."""
    if raw is None:
        return None
    try:
        payload = json.loads(raw)
        return CacheEntry(
            updated=int(payload["updated"]),
            items=[NewsItem.model_validate(item) for item in payload["items"]],
        )
    except (ValueError, KeyError, TypeError):
        return None


async def get(redis: Redis, source_id: str, sort: str = "hot") -> CacheEntry | None:
    return parse_entry(await redis.get(cache_key(source_id, sort)))


async def mget_hot_raw(
    redis: Redis, source_ids: list[str]
) -> list[tuple[str, str | bytes | None]]:
    """Fetch the raw canonical (hot) payloads for many sources in a single
    round trip, paired with their source id in input order. Callers parse
    lazily (see `parse_entry`) so a bounded result set doesn't force
    deserializing every entry up front."""
    if not source_ids:
        return []
    raws = await redis.mget([cache_key(source_id) for source_id in source_ids])
    return list(zip(source_ids, raws, strict=True))


async def set(
    redis: Redis, source_id: str, items: list[NewsItem], sort: str = "hot"
) -> int:
    updated = now_ms()
    payload = json.dumps(
        {
            "updated": updated,
            "items": [
                item.model_dump(by_alias=True, exclude_none=True) for item in items
            ],
        },
        ensure_ascii=False,
    )
    await redis.set(cache_key(source_id, sort), payload, ex=TTL_MS // 1000)
    return updated
