"""News search.

Two cheap, fetch-free passes:

- **sources** — substring match over the static source roster (always works,
  even cold).
- **headlines** — substring match over items already in the Redis cache. We
  only ever read warm entries (never trigger an outbound fetch), so a query
  finds headlines from sources the wall has recently served. Cold sources are
  simply absent.
"""

from polar.redis import Redis

from . import cache
from .metadata import SOURCES
from .schemas import NewsSearchItem, SourceMeta

# Hot-feed cache keys look like ``news:source:{id}``; sorted variants add a
# ``:{sort}`` suffix. Restrict the scan to the canonical hot feed so the same
# headline isn't returned once per sort.
_HOT_KEY_PARTS = 3
_SCAN_LIMIT = 600  # cap keys scanned so a huge warm cache can't stall a query


def search_sources(query: str, *, limit: int = 20) -> list[SourceMeta]:
    q = query.lower()
    hits: list[SourceMeta] = []
    for source_id, meta in SOURCES.items():
        if meta.get("redirect"):
            continue
        name = str(meta.get("name", ""))
        if q in source_id.lower() or q in name.lower():
            hits.append(
                SourceMeta.model_validate(
                    {
                        "id": source_id,
                        "interval": meta.get("interval", cache.DEFAULT_INTERVAL_MS),
                        **{
                            k: v
                            for k, v in meta.items()
                            if k in ("name", "color", "column", "type", "home")
                        },
                    }
                )
            )
            if len(hits) >= limit:
                break
    return hits


async def search_headlines(
    redis: Redis, query: str, *, limit: int = 30
) -> list[NewsSearchItem]:
    q = query.lower()
    hits: list[NewsSearchItem] = []
    scanned = 0

    async for raw_key in redis.scan_iter(match="news:source:*", count=200):
        scanned += 1
        if scanned > _SCAN_LIMIT:
            break
        key = raw_key.decode() if isinstance(raw_key, bytes) else raw_key
        if key.count(":") != _HOT_KEY_PARTS - 1:
            continue  # skip sorted variants
        source_id = key.rsplit(":", 1)[-1]

        entry = await cache.get(redis, source_id)
        if entry is None:
            continue
        source_name = str(SOURCES.get(source_id, {}).get("name", source_id))
        for item in entry.items:
            if q in item.title.lower():
                hits.append(
                    NewsSearchItem(
                        source_id=source_id, source_name=source_name, item=item
                    )
                )
                if len(hits) >= limit:
                    return hits
    return hits
