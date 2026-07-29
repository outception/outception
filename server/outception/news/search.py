"""News search.

Two cheap, fetch-free passes:

- **sources** — substring match over the static source roster (always works,
  even cold).
- **headlines** — substring match over items already in the Redis cache. We
  only ever read warm entries (never trigger an outbound fetch), so a query
  finds headlines from sources the wall has recently served. Cold sources are
  simply absent.
"""

import re
from collections.abc import Iterator

import structlog

from outception.redis import Redis

from . import cache
from .metadata import SOURCES
from .registry import DISABLED_SOURCES
from .schemas import NewsSearchItem, SourceMeta

log = structlog.get_logger()

# Every source that can appear on the wall, in roster order. Only the canonical
# (hot) key is read, so a headline isn't returned once per sort variant.
_SEARCHABLE_SOURCE_IDS: list[str] = [
    source_id
    for source_id, meta in SOURCES.items()
    if source_id not in DISABLED_SOURCES and not meta.get("redirect")
]
_MGET_CHUNK = 250  # keep any single MGET off Redis' hot path for too long

# Entries that pass the title gate below still pay a full model parse each;
# past this many gate hits the scan stops with what it has, so a query that
# matches half the warm roster can't parse thousands of entries for a
# 30-item response.
#
# Since the gate matches TITLES only, a gate hit all but guarantees a real hit,
# so `limit` is normally reached long before this — it can realistically only
# trip on entries that gate-match and then fail to parse. It is a backstop, not
# a routine bound, so tripping it is logged rather than silently truncating the
# results.
_MAX_MATCHED_ENTRIES = 400

# The cache stores ensure_ascii=False JSON, so `"title": "..."` values appear
# verbatim (modulo \" and \\ escapes). Extracting them is a fraction of the
# cost of lowercasing the whole payload per request.
_TITLE_RE = re.compile(r'"title":\s*"((?:[^"\\]|\\.)*)"')


def _chunks(items: list[str], size: int) -> Iterator[list[str]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def _title_blob(raw: str | bytes) -> str:
    """All `"title"` values in a raw cache payload, joined and lowercased —
    the substring gate runs against this instead of the ~50x larger payload."""
    text = raw.decode("utf-8", "ignore") if isinstance(raw, bytes) else raw
    return "\n".join(_TITLE_RE.findall(text)).lower()


def _probes(q: str) -> tuple[re.Pattern[bytes] | None, re.Pattern[str]]:
    """A cheap first-pass probe for *q* over a RAW payload, as (bytes, str).

    A title match implies a payload match, so anything the probe rejects
    cannot hold a hit — and rejecting is the common case. It matters because
    the title gate is not cheap: it decodes the payload, regex-scans it, joins
    and lowercases the result, for every warm entry on the roster. That was
    ~55 ms of event-loop CPU for a query matching nothing — time in which the
    process serves no other request.

    The bytes probe skips even the decode, but `IGNORECASE` on bytes folds
    ASCII only, so a non-ASCII query (Cyrillic, Greek) falls back to the str
    probe rather than silently missing capitalised forms of its own alphabet.
    """
    pattern = re.escape(q)
    return (
        re.compile(pattern.encode(), re.IGNORECASE) if q.isascii() else None,
        re.compile(pattern, re.IGNORECASE),
    )


async def _warm_source_ids(redis: Redis) -> tuple[list[str], bool]:
    """The sources worth reading, in roster order, plus whether that came from
    the warm index.

    The roster is ~10,000 sources and barely a hundred are warm at any moment,
    so asking Redis for all of them cost 41 round trips of almost entirely nil
    replies — the bulk of a search. The index (`cache.WARM_SOURCES_KEY`) is a
    hint maintained on write; an empty one means it has not been populated yet
    (a fresh Redis, or the first run after this shipped), and the caller then
    falls back to the full roster and backfills from what it finds — so search
    can never go blind waiting for the index to warm up.
    """
    members = await redis.smembers(cache.WARM_SOURCES_KEY)
    if not members:
        return list(_SEARCHABLE_SOURCE_IDS), False
    warm = {m.decode() if isinstance(m, bytes) else str(m) for m in members}
    # Filtered through the roster rather than used directly: roster order keeps
    # results stable, and an id that has since left the roster (disabled, or a
    # redirect alias) must not come back through the index.
    return [sid for sid in _SEARCHABLE_SOURCE_IDS if sid in warm], True


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
    probe_bytes, probe_str = _probes(q)
    # Ids the index claimed were warm but that hold nothing (their entry aged
    # out), and — when the index was cold — the ones that really are warm.
    # Applied once at the end so the scan itself stays read-only.
    stale: list[str] = []
    found: list[str] = []

    candidates, from_index = await _warm_source_ids(redis)

    # `finally`, so a scan that stops early — limit reached, backstop tripped —
    # still leaves the index better than it found it. Nothing here can change
    # the result; it only corrects what the NEXT search will read.
    try:
        await _scan(
            redis,
            candidates,
            q,
            limit,
            hits,
            probe_bytes,
            probe_str,
            stale,
            found,
            from_index,
        )
    finally:
        pipe = redis.pipeline()
        if stale:
            pipe.srem(cache.WARM_SOURCES_KEY, *stale)
        if found:
            pipe.sadd(cache.WARM_SOURCES_KEY, *found)
        if stale or found:
            await pipe.execute()
    return hits


async def _scan(
    redis: Redis,
    candidates: list[str],
    q: str,
    limit: int,
    hits: list[NewsSearchItem],
    probe_bytes: "re.Pattern[bytes] | None",
    probe_str: "re.Pattern[str]",
    stale: list[str],
    found: list[str],
    from_index: bool,
) -> None:
    """Fill *hits* from the warm entries of *candidates*, noting index
    corrections in *stale* / *found* for the caller to apply."""
    matched_entries = 0
    # Read the candidates by name. Scanning for them instead walks the WHOLE
    # keyspace — which is dominated by the per-headline, per-language
    # translation cache — so a single search became millions of keys' worth of
    # SCAN round trips. The roster is static and known at import time.
    for chunk in _chunks(candidates, _MGET_CHUNK):
        # One MGET per chunk (vs a GET per key), parsed lazily so filling
        # `limit` from the first few sources doesn't deserialize all of them.
        for source_id, raw in await cache.mget_hot_raw(redis, chunk):
            if raw is None:
                if from_index:
                    stale.append(source_id)
            elif not from_index:
                found.append(source_id)
            # Two gates before the expensive model parse, cheapest first: the
            # raw probe (see _probes) throws out the entries that cannot hold
            # the query at all, then the titles-only check confirms the match
            # is in a title rather than a url or description. Only titles are
            # matched downstream, so neither can hide a real hit.
            if raw is not None:
                if probe_bytes is not None and isinstance(raw, bytes):
                    if probe_bytes.search(raw) is None:
                        continue
                else:
                    text = (
                        raw.decode("utf-8", "ignore") if isinstance(raw, bytes) else raw
                    )
                    if probe_str.search(text) is None:
                        continue
                if q not in _title_blob(raw):
                    continue
                matched_entries += 1
                if matched_entries > _MAX_MATCHED_ENTRIES:
                    log.info(
                        "news.search_scan_capped",
                        matched_entries=matched_entries,
                        hits=len(hits),
                        limit=limit,
                    )
                    return
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
                        return
