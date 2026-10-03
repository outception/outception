"""The builder: one ranked briefing per profile from the last day's
scored clusters, under the profile's threshold and category quotas,
written to Redis for the route and to Postgres for history."""

import json
from datetime import UTC, datetime
from typing import Any

import structlog

from outception.cards.schemas import BriefingItem, BriefingPublisher
from outception.kit.utils import utc_now
from outception.models import NewsBriefing, NewsCluster, NewsClusterScore
from outception.postgres import AsyncSession
from outception.redis import Redis

from ..clusters import repository
from ..registry import SOURCES
from ..schemas import NewsItem
from .profiles import Profile

log = structlog.get_logger()

LATEST_KEY = "news:briefing:{profile}:latest"
BUILT_AT_KEY = "news:briefing:{profile}:built_at"
LOCK_KEY = "news:briefing:lock:{profile}"
LOCK_SECONDS = 10 * 60
WINDOW_HOURS = 24
STALE_AFTER_MS = 2 * 3600 * 1000
PUBLISHERS_SHOWN = 8


def _publisher(source_id: str) -> BriefingPublisher:
    meta = SOURCES.get(source_id, {})
    return BriefingPublisher(
        source_id=source_id,
        name=str(meta.get("name") or source_id),
        logo=str(meta.get("logo") or "") or None,
    )


async def _item(
    session: AsyncSession, cluster: NewsCluster, score: NewsClusterScore
) -> BriefingItem | None:
    members = await repository.members(session, cluster.id)
    if not members:
        return None
    lead = members[0]
    publishers = list(dict.fromkeys(member.source_id for member in members))
    news_item = NewsItem(
        id=lead.item_id,
        title=lead.title,
        url=lead.url,
        pub_date=int(lead.pub_date.timestamp() * 1000) if lead.pub_date else None,
    )
    return BriefingItem(
        cluster_id=str(cluster.id),
        title=cluster.title,
        url=lead.url,
        score=score.score,
        category=score.category or "other",
        why=score.why,
        publisher_count=cluster.publisher_count,
        publishers=[_publisher(sid) for sid in publishers[:PUBLISHERS_SHOWN]],
        pub_date=news_item.pub_date,
        lead_source_name=_publisher(cluster.lead_source_id).name,
        item=news_item,
    )


def select_items(
    profile: Profile, candidates: list[BriefingItem]
) -> tuple[list[BriefingItem], dict[str, int]]:
    """Threshold, per-category quota, total cap; the input is already in
    score, publisher count, recency order."""
    quota = {category.id: category.max for category in profile.categories}
    taken: dict[str, int] = {}
    chosen: list[BriefingItem] = []
    for item in candidates:
        if item.score is None or item.score < profile.min_score:
            continue
        category = item.category if item.category in quota else "other"
        limit = quota.get(category, 0) if category != "other" else 0
        if taken.get(category, 0) >= limit:
            continue
        taken[category] = taken.get(category, 0) + 1
        chosen.append(item)
        if len(chosen) >= profile.max_items:
            break
    return chosen, taken


async def build(
    session: AsyncSession, redis: Redis, profile: Profile
) -> NewsBriefing | None:
    """Build and publish one briefing; None when another build holds the
    lock."""
    lock = LOCK_KEY.format(profile=profile.id)
    if not await redis.set(lock, "1", ex=LOCK_SECONDS, nx=True):
        return None
    try:
        scored = await repository.scored_recent(session, profile.id, hours=WINDOW_HOURS)
        candidates: list[BriefingItem] = []
        nulls = 0
        for cluster, score in scored:
            item = await _item(session, cluster, score)
            if item is not None:
                candidates.append(item)
        items, per_category = select_items(profile, candidates)
        now = utc_now()
        items_json: list[dict[str, Any]] = [
            item.model_dump(by_alias=True, mode="json") for item in items
        ]
        stats = {
            "candidates": len(candidates),
            "nulls": nulls,
            "per_category": per_category,
            "window_hours": WINDOW_HOURS,
        }
        briefing = NewsBriefing(
            profile_id=profile.id,
            built_for=now.date(),
            built_at=now,
            items=items_json,
            stats=stats,
        )
        session.add(briefing)
        await session.flush()
        built_at_ms = int(now.timestamp() * 1000)
        payload = {
            "profile": profile.id,
            "builtAt": built_at_ms,
            "staleAfterMs": STALE_AFTER_MS,
            "items": items_json,
        }
        pipe = redis.pipeline()
        pipe.set(
            LATEST_KEY.format(profile=profile.id),
            json.dumps(payload, ensure_ascii=False),
        )
        pipe.set(BUILT_AT_KEY.format(profile=profile.id), str(built_at_ms))
        await pipe.execute()
        log.info("news.build_briefing", profile=profile.id, items=len(items))
        return briefing
    finally:
        await redis.delete(lock)


def built_at_of(raw: str | bytes | None) -> datetime | None:
    if raw is None:
        return None
    try:
        return datetime.fromtimestamp(int(raw) / 1000, tz=UTC)
    except ValueError, TypeError, OSError:
        return None
