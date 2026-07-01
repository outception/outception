"""Redis cache for fetched news items.

Two timescales (ported semantics):
  - per-source ``interval`` (metadata, default 10 min): content fresher
    than this is served as ``status:"success"`` without refetching.
  - global ``TTL`` (30 min): content older than ``interval`` but younger
    than this is served as ``status:"cache"``; beyond it we refetch.

Redis ``ex=`` is set to the hard TTL so keys self-expire; the softer
``interval`` comparison happens in Python against the stored timestamp.
"""

import json
import time
from dataclasses import dataclass

from outception.redis import Redis

from .schemas import NewsItem

TTL_MS = 30 * 60 * 1000
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


async def get(redis: Redis, source_id: str, sort: str = "hot") -> CacheEntry | None:
    raw = await redis.get(cache_key(source_id, sort))
    if raw is None:
        return None
    try:
        payload = json.loads(raw)
        return CacheEntry(
            updated=int(payload["updated"]),
            items=[NewsItem.model_validate(item) for item in payload["items"]],
        )
    except (ValueError, KeyError, TypeError):
        # A malformed entry is a cache miss, not an error.
        return None


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
