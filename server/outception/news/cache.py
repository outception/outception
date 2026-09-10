"""Redis cache for fetched news items.

Two timescales (ported semantics):
  - per-source ``interval`` (metadata, default 2 min): content fresher
    than this is served as ``status:"success"`` without refetching. A source
    older than its interval is refetched on the next ``latest`` request (the
    wall polls each visible card with ``latest=true``), bounded to one outbound
    fetch per source per cooldown window in the endpoint.
  - global ``TTL`` (3 h): content older than ``interval`` but younger
    than this is served as ``status:"cache"``; beyond it we refetch. The
    window is generous so rate-limited sources warmed on a slow rotation
    stay served from cache between passes.

Redis ``ex=`` is set to the hard TTL so keys self-expire; the softer
``interval`` comparison happens in Python against the stored timestamp.
"""

import hashlib
import json
import time
from dataclasses import dataclass

from outception.redis import Redis

from .schemas import NewsItem

TTL_MS = 180 * 60 * 1000
DEFAULT_INTERVAL_MS = 2 * 60 * 1000

_KEY = "news:source:{id}"
_KEY_SORTED = "news:source:{id}:{sort}"

# Which sources currently hold a canonical (hot) entry - maintained by `set`
# and pruned by readers. See the comment there for why it exists.
WARM_SOURCES_KEY = "news:warm-sources"

# A source's headline titles alone, lowercased, one per line. Headline search
# substring-scans every warm source on every query, and over the full payloads
# that is 8.5 MB and ~39 ms of event-loop CPU for a query matching nothing -
# measured in production, and every prefix a reader types on the way to a real
# query IS such a query. Titles are 12.6% of the payload, so scanning these
# instead costs ~4 ms. Written here so the read path never has to extract them.
_TITLES_KEY = "news:titles:{id}"


def titles_key(source_id: str) -> str:
    """Redis key holding *source_id*'s lowercased titles, for search's gate."""
    return _TITLES_KEY.format(id=source_id)


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


async def mget_titles(
    redis: Redis, source_ids: list[str]
) -> list[tuple[str, str | bytes | None]]:
    """Fetch many sources' lowercased title blobs in one round trip, paired
    with their source id in input order. None means the source has no blob -
    either it is cold, or its entry predates this key - and the caller must
    fall back to the full payload rather than treat it as "no match"."""
    if not source_ids:
        return []
    blobs = await redis.mget([titles_key(source_id) for source_id in source_ids])
    return list(zip(source_ids, blobs, strict=True))


TEASER_TTL_SECONDS = 7 * 24 * 60 * 60
KNOWN_TTL_SECONDS = 7 * 24 * 60 * 60


def teaser_key(url: str) -> str:
    return f"news:teaser:{hashlib.sha256(url.encode('utf-8')).hexdigest()[:32]}"


def known_key(url: str) -> str:
    return f"news:known:{hashlib.sha256(url.encode('utf-8')).hexdigest()[:32]}"


async def is_known(redis: Redis, url: str) -> bool:
    """Whether *url* is a headline the wall itself served recently."""
    return bool(await redis.exists(known_key(url)))


# Stamped whenever a source's items were just remembered, so the serving path
# (`endpoints._keep_known`) refreshes the index on a slow cadence instead of
# re-writing it right after every fetch.
KNOWN_REFRESH_KEY = "news:known:refresh:{id}"
KNOWN_REFRESH_SECONDS = 10 * 60


async def remember_items(
    redis: Redis, items: list[NewsItem], *, source_id: str | None = None
) -> None:
    """Remember each item by URL: that we serve it (see `is_known`), and the
    publisher's standfirst where the feed carries one (see NewsItem.teaser)."""
    if not items:
        return
    pipe = redis.pipeline()
    for item in items:
        pipe.set(known_key(item.url), "1", ex=KNOWN_TTL_SECONDS)
        if item.teaser:
            pipe.set(teaser_key(item.url), item.teaser, ex=TEASER_TTL_SECONDS)
    if source_id is not None:
        pipe.set(KNOWN_REFRESH_KEY.format(id=source_id), "1", ex=KNOWN_REFRESH_SECONDS)
    await pipe.execute()


async def get_teaser(redis: Redis, url: str) -> str | None:
    value = await redis.get(teaser_key(url))
    if value is None:
        return None
    return value.decode() if isinstance(value, bytes) else value


async def set(
    redis: Redis, source_id: str, items: list[NewsItem], sort: str = "hot"
) -> int:
    await remember_items(redis, items, source_id=source_id)
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
    pipe = redis.pipeline()
    pipe.set(cache_key(source_id, sort), payload, ex=TTL_MS // 1000)
    if sort == "hot":
        # Same TTL as the payload, so the two can never disagree about whether
        # a source is warm.
        pipe.set(
            titles_key(source_id),
            "\n".join(item.title for item in items if item.title).lower(),
            ex=TTL_MS // 1000,
        )
        # Note which sources actually hold a canonical entry. The roster is
        # ~10,000 sources but only a hundred-odd are ever warm at once, and
        # headline search used to MGET the whole roster to find them - 41 round
        # trips whose replies were ~99% nils. Members outlive their entries
        # (the set has no per-member TTL), so this is a HINT: search prunes the
        # ids that come back empty (see search._warm_source_ids).
        pipe.sadd(WARM_SOURCES_KEY, source_id)
    await pipe.execute()
    return updated
