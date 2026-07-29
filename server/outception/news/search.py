"""News search.

Two cheap, fetch-free passes:

- **sources** — substring match over the static source roster (always works,
  even cold).
- **headlines** — substring match over items already in the Redis cache. We
  only ever read warm entries (never trigger an outbound fetch), so a query
  finds headlines from sources the wall has recently served. Cold sources are
  simply absent.
"""

from collections.abc import Iterator

from outception.redis import Redis

from . import cache
from .metadata import SOURCES
from .registry import DISABLED_SOURCES
from .schemas import NewsSearchItem, SourceMeta

# Every source that can appear on the wall, in roster order. Only the canonical
# (hot) key is read, so a headline isn't returned once per sort variant.
_SEARCHABLE_SOURCE_IDS: list[str] = [
    source_id
    for source_id, meta in SOURCES.items()
    if source_id not in DISABLED_SOURCES and not meta.get("redirect")
]
_MGET_CHUNK = 250  # keep any single MGET off Redis' hot path for too long


def _chunks(items: list[str], size: int) -> Iterator[list[str]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def search_sources(query: str, *, limit: int = 20) -> list[SourceMeta]:
    q = query.lower()
    hits: list[SourceMeta] = []
    for source_id, meta in SOURCES.items():
        if meta.get("redirect") or source_id in DISABLED_SOURCES:
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

    # Read the candidates by name. Scanning for them instead walks the WHOLE
    # keyspace — which is dominated by the per-headline, per-language
    # translation cache — so a single search became millions of keys' worth of
    # SCAN round trips. The roster is static and known at import time.
    for chunk in _chunks(_SEARCHABLE_SOURCE_IDS, _MGET_CHUNK):
        # One MGET per chunk (vs a GET per key), parsed lazily so filling
        # `limit` from the first few sources doesn't deserialize all of them.
        for source_id, raw in await cache.mget_hot_raw(redis, chunk):
            # Cheap raw-substring gate before the expensive model parse: a
            # no-match search otherwise deserializes every warm entry (~430 ms
            # of event-loop stall across a 5,700-source roster). The cache
            # stores ensure_ascii=False JSON, so the decoded raw contains the
            # titles verbatim — a miss here can never hide a real hit.
            if raw is not None:
                text = raw.decode("utf-8", "ignore") if isinstance(raw, bytes) else raw
                if q not in text.lower():
                    continue
            entry = cache.parse_entry(raw)
            if entry is None:
                continue  # cold source: never fetched, simply absent
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
