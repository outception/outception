"""The two actors that keep clusters current: the sweep drains the pending
set the cache writer feeds (no model), and the resolver asks one batch
of typed questions for the borderline pairs."""

import time
from typing import Any
from uuid import UUID

import structlog
from redis import RedisError

from outception.config import settings
from outception.jobs import record_run
from outception.locker import Locker, TimeoutLockError
from outception.models import JobKind
from outception.redis import create_redis
from outception.worker import (
    AsyncSessionMaker,
    CronTrigger,
    TaskPriority,
    TaskQueue,
    actor,
)

from .. import cache
from ..briefing.questions import resolve_questions
from ..summaries.providers.base import Decision, Question
from ..summaries.providers.chain import ChainExhausted
from ..summaries.providers.classes import ModelError
from ..summaries.providers.lanes import Consumer, Lane
from ..summaries.providers.registry import build_chains
from . import repository, service
from .decisions import record_shadow

log = structlog.get_logger()

SWEEP_LOCK = "news.cluster_sweep"
SWEEP_SOURCES_PER_RUN = 60
SWEEP_BUDGET_SECONDS = 90
RESOLVE_LOCK = "news.resolve_borderline"
RESOLVE_PAIRS_PER_RUN = 20


@actor(
    actor_name="news.cluster_sweep",
    cron_trigger=CronTrigger(minute="*/2"),
    queue_name=TaskQueue.NEWS_PIPELINE,
    priority=TaskPriority.LOW,
    max_retries=0,
    time_limit=(SWEEP_BUDGET_SECONDS + 30) * 1000,
)
async def cluster_sweep() -> None:
    redis = create_redis("worker")
    sources = 0
    totals = service.IngestStats()
    deadline = time.monotonic() + SWEEP_BUDGET_SECONDS
    try:
        async with Locker(redis).lock(
            SWEEP_LOCK, timeout=SWEEP_BUDGET_SECONDS + 30, blocking_timeout=0
        ):
            pending = await service.pop_pending(redis, SWEEP_SOURCES_PER_RUN)
            async with AsyncSessionMaker() as session:
                clusterer = service.Clusterer(session, redis)
                for source_id in pending:
                    if time.monotonic() > deadline:
                        await service.note_pending(redis, source_id)
                        continue
                    entry = await cache.get(redis, source_id)
                    if entry is None or not entry.items:
                        continue
                    stats = await clusterer.ingest(source_id, entry.items)
                    await session.commit()
                    sources += 1
                    totals.joined_by_url += stats.joined_by_url
                    totals.joined_by_text += stats.joined_by_text
                    totals.borderline += stats.borderline
                    totals.created += stats.created
    except TimeoutLockError:
        return
    except RedisError as exc:
        log.info("news.cluster_sweep.redis_unavailable", error=str(exc))
        return
    finally:
        await redis.close()
    log.info(
        "news.cluster_sweep",
        sources=sources,
        by_url=totals.joined_by_url,
        by_text=totals.joined_by_text,
        borderline=totals.borderline,
        created=totals.created,
    )


async def _pair_state(session: Any, pair: dict[str, object]) -> dict[str, Any] | None:
    try:
        new_id, candidate_id = UUID(str(pair["new"])), UUID(str(pair["candidate"]))
    except KeyError, ValueError:
        return None
    new = await repository.get(session, new_id)
    candidate = await repository.get(session, candidate_id)
    if new is None or candidate is None:
        return None
    return {
        "new_id": new_id,
        "candidate_id": candidate_id,
        "a": {"title": new.title, "publishers": new.publisher_count},
        "b": {"title": candidate.title, "publishers": candidate.publisher_count},
        "estimate": pair.get("estimate"),
    }


async def resolve_pairs(
    session: Any, redis: Any, pairs: list[dict[str, object]]
) -> int:
    """One decision call for a batch of pairs; merges where the answer is
    yes. Returns the merged count. Raises `ChainExhausted` so the caller
    can put the pairs back."""
    states = [s for s in [await _pair_state(session, pair) for pair in pairs] if s]
    if not states:
        return 0
    questions: list[Question] = resolve_questions(len(states))
    state = {
        "pairs": [
            {"id": q.id, "a": s["a"]["title"], "b": s["b"]["title"]}
            for q, s in zip(questions, states, strict=True)
        ]
    }
    chains = build_chains(redis)
    async with record_run(
        session, JobKind.resolve, f"{len(states)} pairs", lane=Lane.background
    ) as run:
        decision: Decision = await chains.decide(
            "resolve",
            state,
            questions,
            consumer=Consumer.resolve,
            shadow=record_shadow(redis, "resolve"),
        )
        run.served(decision.model)
    merged = 0
    clusterer = service.Clusterer(session, redis)
    for question, pair_state in zip(questions, states, strict=True):
        answer = decision.answers.get(question.id)
        if answer is not None and answer.chosen == "true":
            merged += int(
                bool(
                    await clusterer.merge(
                        pair_state["candidate_id"], pair_state["new_id"]
                    )
                )
            )
    return merged


@actor(
    actor_name="news.resolve_borderline",
    cron_trigger=CronTrigger(minute="*/5"),
    queue_name=TaskQueue.NEWS_PIPELINE,
    priority=TaskPriority.LOW,
    max_retries=0,
    time_limit=4 * 60 * 1000,
)
async def resolve_borderline() -> None:
    if settings.LLM_DISABLED:
        return
    redis = create_redis("worker")
    merged = 0
    try:
        async with Locker(redis).lock(RESOLVE_LOCK, timeout=5 * 60, blocking_timeout=0):
            pairs = await service.pop_borderline(redis, RESOLVE_PAIRS_PER_RUN)
            if not pairs:
                return
            async with AsyncSessionMaker() as session:
                try:
                    merged = await resolve_pairs(session, redis, pairs)
                    await session.commit()
                except (ChainExhausted, ModelError) as exc:
                    await session.commit()
                    log.info("news.resolve_borderline.deferred", error=str(exc))
                    for pair in pairs:
                        await redis.rpush(
                            service.BORDERLINE_KEY, __import__("json").dumps(pair)
                        )
    except TimeoutLockError:
        return
    except RedisError as exc:
        log.info("news.resolve_borderline.redis_unavailable", error=str(exc))
        return
    finally:
        await redis.close()
    log.info("news.resolve_borderline", merged=merged)
