"""The scorer: for each pending cluster of a profile, one decision call
(score and category as typed questions) and one short generation for
the why line, both on the background lane under the score sub-cap. Every
reply is data under a contract; null beats a crash."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog

from outception.jobs import record_run
from outception.kit.utils import utc_now
from outception.models import JobKind, NewsClusterScore
from outception.net.scrub import scrub
from outception.postgres import AsyncSession
from outception.redis import Redis

from ..clusters import repository
from ..clusters.decisions import record_shadow
from ..registry import SOURCES
from ..summaries.providers.chain import ChainExhausted, Chains
from ..summaries.providers.classes import ModelError
from ..summaries.providers.lanes import Consumer, Lane
from ..summaries.providers.registry import build_chains
from . import prompts
from .profiles import Profile
from .questions import score_questions

log = structlog.get_logger()

PENDING_KEY = "news:score:pending:{profile}"
DAY_KEY = "news:score:day:{day}"
CALLS_HOUR_KEY = "news:score:calls:{hour}"
NULLS_HOUR_KEY = "news:score:nulls:{hour}"
BATCH = 10
WHY_MAX_CHARS = 140
# A scored cluster is not re-scored for a day unless its publisher count
# doubled since.
RESCORE_SECONDS = 24 * 3600


@dataclass
class ScoreStats:
    scored: int = 0
    nulls: int = 0
    skipped: int = 0
    deferred: bool = False


async def note_pending(redis: Redis, profile_id: str, cluster_ids: list[UUID]) -> None:
    if cluster_ids:
        await redis.sadd(
            PENDING_KEY.format(profile=profile_id), *[str(c) for c in cluster_ids]
        )


async def _pop(redis: Redis, profile_id: str, count: int) -> list[UUID]:
    raw = await redis.spop(PENDING_KEY.format(profile=profile_id), count)
    if raw is None:
        return []
    values = raw if isinstance(raw, list) else [raw]
    out: list[UUID] = []
    for value in values:
        try:
            out.append(UUID(value.decode() if isinstance(value, bytes) else str(value)))
        except ValueError:
            continue
    return out


def _state(cluster: Any, source_ids: list[str]) -> dict[str, Any]:
    names = [str(SOURCES.get(sid, {}).get("name") or sid) for sid in source_ids[:8]]
    age_hours = max(0.0, (utc_now() - cluster.first_seen_at).total_seconds() / 3600)
    return {
        "title": cluster.title,
        "publisher_count": cluster.publisher_count,
        "sources": names,
        "age_hours": round(age_hours, 1),
    }


async def _why(chains: Chains, profile: Profile, cluster: Any) -> str | None:
    try:
        reply = await chains.generate(
            prompts.why_prompt(profile, cluster.title, cluster.publisher_count),
            Lane.background,
            consumer=Consumer.score,
        )
    except ChainExhausted, ModelError:
        return None
    line = scrub(" ".join(reply.text.split()))
    line = line.replace('"', "").replace("—", ",").replace("–", ",")
    return line[:WHY_MAX_CHARS] or None


async def _count(redis: Redis, *, null: bool) -> None:
    now = datetime.now(UTC)
    hour, day = now.strftime("%Y%m%d%H"), now.strftime("%Y%m%d")
    pipe = redis.pipeline()
    pipe.incr(CALLS_HOUR_KEY.format(hour=hour))
    pipe.expire(CALLS_HOUR_KEY.format(hour=hour), 3 * 3600)
    pipe.incr(DAY_KEY.format(day=day))
    pipe.expire(DAY_KEY.format(day=day), 2 * 86400)
    if null:
        pipe.incr(NULLS_HOUR_KEY.format(hour=hour))
        pipe.expire(NULLS_HOUR_KEY.format(hour=hour), 3 * 3600)
    await pipe.execute()


async def score_one(
    session: AsyncSession,
    redis: Redis,
    chains: Chains,
    profile: Profile,
    cluster_id: UUID,
) -> NewsClusterScore | None:
    cluster = await repository.get(session, cluster_id)
    if cluster is None:
        return None
    existing = await repository.score_for(session, cluster_id, profile.id)
    if (
        existing is not None
        and (utc_now() - existing.scored_at).total_seconds() < RESCORE_SECONDS
        and cluster.publisher_count < 2 * max(existing.publisher_count, 1)
    ):
        return existing
    members = await repository.members(session, cluster_id)
    source_ids = list(dict.fromkeys(member.source_id for member in members))
    state = _state(cluster, source_ids)
    questions = score_questions(profile)
    score: int | None = None
    category: str | None = None
    provider = "none"
    tokens = (0, 0)
    try:
        async with record_run(
            session,
            JobKind.score,
            str(cluster_id),
            lane=Lane.background,
            prompt_version=str(prompts.score_version()),
            prompt=prompts.rubric_block(profile),
        ) as run:
            decision = await chains.decide(
                "score",
                {
                    **state,
                    "policy": prompts.rubric_block(profile),
                    "rules": prompts.system_rules(),
                },
                questions,
                consumer=Consumer.score,
                shadow=record_shadow(redis, "score"),
            )
            run.served(decision.model)
            provider = decision.model
            answer = decision.answers.get("score")
            if answer is not None:
                score = int(answer.chosen)
            chosen_category = decision.answers.get("category")
            if chosen_category is not None:
                category = chosen_category.chosen
    except ChainExhausted:
        raise
    except ModelError as exc:
        log.info("news.score_failed", cluster=str(cluster_id), error=str(exc))
    why = None
    if score is not None and score >= profile.min_score:
        why = await _why(chains, profile, cluster)
    row = existing or NewsClusterScore(
        cluster_id=cluster_id, profile_id=profile.id, provider=provider
    )
    row.score = score
    row.category = category
    row.why = why
    row.provider = provider
    row.tokens_in, row.tokens_out = tokens
    row.scored_at = utc_now()
    row.publisher_count = cluster.publisher_count
    if existing is None:
        session.add(row)
    await session.flush()
    await _count(redis, null=score is None)
    return row


async def score_pending(
    session: AsyncSession, redis: Redis, profile: Profile, *, batch: int = BATCH
) -> ScoreStats:
    """Drain up to `batch` pending clusters. Stops cleanly when the lane
    cap is hit and leaves the rest pending."""
    stats = ScoreStats()
    chains = build_chains(redis)
    cluster_ids = await _pop(redis, profile.id, batch)
    for index, cluster_id in enumerate(cluster_ids):
        try:
            row = await score_one(session, redis, chains, profile, cluster_id)
        except ChainExhausted:
            await note_pending(redis, profile.id, cluster_ids[index:])
            stats.deferred = True
            break
        if row is None:
            stats.skipped += 1
        elif row.score is None:
            stats.nulls += 1
        else:
            stats.scored += 1
        await session.commit()
    return stats
