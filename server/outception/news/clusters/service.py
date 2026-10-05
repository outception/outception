"""The clusterer: cheap first (the URL key), then MinHash candidates from
the band buckets, then the model only for a borderline pair. Duplicates
are never dropped: a member is always kept and the publisher count is the
weight. No single model call ever lists everything."""

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID

import structlog

from outception.kit.utils import utc_now
from outception.postgres import AsyncSession
from outception.redis import Redis

from ..schemas import NewsItem
from . import minhash, repository
from .urlkey import url_key

log = structlog.get_logger()

URL_KEY = "news:cluster:url:{sha}"
LSH_KEY = f"news:cluster:lsh{minhash.SCHEME}:{{band}}:{{sig}}"
SIG_KEY = f"news:cluster:sig{minhash.SCHEME}:{{cluster_id}}"
COUNT_KEY = "news:cluster:pc:{cluster_id}"
PENDING_KEY = "news:cluster:pending"
BORDERLINE_KEY = "news:cluster:borderline"
LOOKUP_TTL_SECONDS = 7 * 24 * 3600
# Measured on cached cards (see minhash.py): rewrites of one story sit at
# 0.6 and above, different stories on one topic at 0.35 and below. The band
# between goes to the resolver.
JOIN_THRESHOLD = 0.6
BORDERLINE_THRESHOLD = 0.4
# Items older than this are history, not news to cluster.
MAX_ITEM_AGE = timedelta(days=7)
MAX_CANDIDATES = 20


@dataclass
class IngestStats:
    joined_by_url: int = 0
    joined_by_text: int = 0
    borderline: int = 0
    created: int = 0
    skipped: int = 0
    touched: set[UUID] = field(default_factory=set)


def _text(item: NewsItem) -> str:
    teaser = item.teaser or (item.extra.info if item.extra and item.extra.info else "")
    return f"{item.title} {teaser}".strip()


def _pub_date(item: NewsItem) -> datetime | None:
    if item.pub_date is None:
        return None
    try:
        return datetime.fromtimestamp(item.pub_date / 1000, tz=UTC)
    except OverflowError, OSError, ValueError:
        return None


async def note_pending(redis: Redis, source_id: str) -> None:
    await redis.sadd(PENDING_KEY, source_id)


async def pop_pending(redis: Redis, count: int) -> list[str]:
    raw = await redis.spop(PENDING_KEY, count)
    if raw is None:
        return []
    values = raw if isinstance(raw, list) else [raw]
    return [v.decode() if isinstance(v, bytes) else str(v) for v in values]


async def cluster_for_urls(redis: Redis, urls: list[str]) -> dict[str, tuple[str, int]]:
    """url -> (cluster id, publisher count) for the urls that are
    clustered: two MGETs, for the envelope's items."""
    if not urls:
        return {}
    ids = await redis.mget([URL_KEY.format(sha=url_key(url)) for url in urls])
    found = {
        url: (cid.decode() if isinstance(cid, bytes) else str(cid))
        for url, cid in zip(urls, ids, strict=True)
        if cid is not None
    }
    if not found:
        return {}
    counts = await redis.mget(
        [COUNT_KEY.format(cluster_id=cid) for cid in found.values()]
    )
    out: dict[str, tuple[str, int]] = {}
    for (url, cid), count in zip(found.items(), counts, strict=True):
        out[url] = (cid, int(count or 1))
    return out


class Clusterer:
    def __init__(self, session: AsyncSession, redis: Redis) -> None:
        self.session = session
        self.redis = redis

    async def _remember(
        self, cluster_id: UUID, key: str, sig: list[int] | None
    ) -> None:
        pipe = self.redis.pipeline()
        pipe.set(URL_KEY.format(sha=key), str(cluster_id), ex=LOOKUP_TTL_SECONDS)
        if sig is not None:
            pipe.set(
                SIG_KEY.format(cluster_id=cluster_id),
                minhash.encode(sig),
                ex=LOOKUP_TTL_SECONDS,
            )
            for band in minhash.band_keys(sig):
                band_key = LSH_KEY.format(
                    band=band.split(":")[0], sig=band.split(":")[1]
                )
                pipe.sadd(band_key, str(cluster_id))
                pipe.expire(band_key, LOOKUP_TTL_SECONDS)
        await pipe.execute()

    async def _publish_count(self, cluster_id: UUID) -> None:
        publishers, _ = await repository.recount(self.session, cluster_id)
        await self.redis.set(
            COUNT_KEY.format(cluster_id=cluster_id),
            str(publishers),
            ex=LOOKUP_TTL_SECONDS,
        )

    async def _candidates(self, sig: list[int]) -> list[tuple[UUID, float]]:
        bands = minhash.band_keys(sig)
        pipe = self.redis.pipeline()
        for band in bands:
            band_id, digest = band.split(":")
            pipe.smembers(LSH_KEY.format(band=band_id, sig=digest))
        buckets = await pipe.execute()
        ids: list[str] = []
        for members in buckets:
            for member in members or ():
                value = member.decode() if isinstance(member, bytes) else str(member)
                if value not in ids:
                    ids.append(value)
        ids = ids[:MAX_CANDIDATES]
        if not ids:
            return []
        stored = await self.redis.mget([SIG_KEY.format(cluster_id=cid) for cid in ids])
        scored: list[tuple[UUID, float]] = []
        for cid, raw in zip(ids, stored, strict=True):
            if raw is None:
                continue
            try:
                scored.append((UUID(cid), minhash.estimate(sig, minhash.decode(raw))))
            except ValueError, TypeError:
                continue
        scored.sort(key=lambda pair: -pair[1])
        return scored

    async def _join(
        self,
        cluster_id: UUID,
        source_id: str,
        item: NewsItem,
        key: str,
        stats: IngestStats,
    ) -> None:
        await repository.add_member(
            self.session,
            cluster_id,
            source_id=source_id,
            item_id=item.id,
            url=item.url,
            url_key=key,
            title=item.title,
            pub_date=_pub_date(item),
        )
        await self._remember(cluster_id, key, None)
        stats.touched.add(cluster_id)

    async def ingest(self, source_id: str, items: list[NewsItem]) -> IngestStats:
        stats = IngestStats()
        now = utc_now()
        for item in items:
            if not item.url or not item.title:
                stats.skipped += 1
                continue
            published = _pub_date(item)
            if published is not None and now - published > MAX_ITEM_AGE:
                stats.skipped += 1
                continue
            key = url_key(item.url)
            known = await self.redis.get(URL_KEY.format(sha=key))
            cluster_id: UUID | None = None
            if known is not None:
                try:
                    cluster_id = UUID(
                        known.decode() if isinstance(known, bytes) else str(known)
                    )
                except ValueError:
                    cluster_id = None
            if cluster_id is None:
                cluster_id = await repository.by_member_url_key(self.session, key)
            if cluster_id is not None:
                await self._join(cluster_id, source_id, item, key, stats)
                stats.joined_by_url += 1
                continue
            sig = minhash.signature(_text(item))
            candidates = await self._candidates(sig)
            best_id, best = candidates[0] if candidates else (None, 0.0)
            if best_id is not None and best >= JOIN_THRESHOLD:
                await self._join(best_id, source_id, item, key, stats)
                stats.joined_by_text += 1
                continue
            cluster = await repository.create(
                self.session, key=key, title=item.title, lead_source_id=source_id
            )
            await repository.add_member(
                self.session,
                cluster.id,
                source_id=source_id,
                item_id=item.id,
                url=item.url,
                url_key=key,
                title=item.title,
                pub_date=published,
            )
            await self._remember(cluster.id, key, sig)
            stats.touched.add(cluster.id)
            stats.created += 1
            if best_id is not None and best >= BORDERLINE_THRESHOLD:
                await self.redis.rpush(
                    BORDERLINE_KEY,
                    json.dumps(
                        {
                            "new": str(cluster.id),
                            "candidate": str(best_id),
                            "estimate": best,
                        }
                    ),
                )
                stats.borderline += 1
        for cluster_id in stats.touched:
            await self._publish_count(cluster_id)
        return stats

    async def merge(self, keep_id: UUID, drop_id: UUID) -> int:
        """Fold `drop_id` into `keep_id`: members move, lookups repoint."""
        dropped = await repository.get(self.session, drop_id)
        if dropped is None:
            return 0
        drop_members = await repository.members(self.session, drop_id)
        moved = await repository.move_members(self.session, drop_id, keep_id)
        pipe = self.redis.pipeline()
        for member in drop_members:
            pipe.set(
                URL_KEY.format(sha=member.url_key), str(keep_id), ex=LOOKUP_TTL_SECONDS
            )
        pipe.delete(
            SIG_KEY.format(cluster_id=drop_id), COUNT_KEY.format(cluster_id=drop_id)
        )
        await pipe.execute()
        await self._publish_count(keep_id)
        return moved


async def pop_borderline(redis: Redis, count: int) -> list[dict[str, object]]:
    pairs: list[dict[str, object]] = []
    for _ in range(count):
        raw = await redis.lpop(BORDERLINE_KEY)
        if raw is None:
            break
        try:
            pairs.append(json.loads(raw))
        except ValueError:
            continue
    return pairs
