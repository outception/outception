"""Promoted slot state: one active run at a time, FIFO queue behind it.

Two Redis keys hold everything:

- ``promoted:active`` - the current ``PromotedSlot`` as JSON, with the key's
  TTL set to the run's remaining time so it self-expires exactly when the
  run ends. No cron needed.
- ``promoted:queue`` - a list of ``QueuedPromotion`` JSON blobs, pushed by
  the operator script and popped here when the active key is empty.

Advancement happens lazily on read: the first cards request after a run
expires pops the next queued promotion and activates it. ``SET NX`` guards
the race where two requests pop concurrently - the loser pushes its pop
back to the FRONT of the queue, preserving order.
"""

from datetime import UTC, datetime, timedelta

from pydantic import ValidationError

from outception.redis import Redis

from .schemas import PromotedSlot, QueuedPromotion

ACTIVE_KEY = "promoted:active"
QUEUE_KEY = "promoted:queue"
# Malformed queue entries land here instead of crashing the public endpoint;
# `python -m scripts.promoted status` surfaces the count.
DEAD_KEY = "promoted:dead"


async def get_active(redis: Redis) -> PromotedSlot | None:
    raw = await redis.get(ACTIVE_KEY)
    if raw is not None:
        return PromotedSlot.model_validate_json(raw)
    return await _advance(redis)


async def _advance(redis: Redis) -> PromotedSlot | None:
    while True:
        raw = await redis.lpop(QUEUE_KEY)
        if raw is None:
            return None
        try:
            queued = QueuedPromotion.model_validate_json(raw)
        except ValidationError:
            await redis.rpush(DEAD_KEY, raw)
            continue
        break
    slot = PromotedSlot(
        id=queued.id,
        business_name=queued.business_name,
        video_url=queued.video_url,
        click_url=queued.click_url,
        tagline=queued.tagline,
        ends_at=datetime.now(UTC) + timedelta(seconds=queued.duration_seconds),
    )
    stored = await redis.set(
        ACTIVE_KEY,
        slot.model_dump_json(by_alias=True),
        ex=queued.duration_seconds,
        nx=True,
    )
    if stored:
        return slot
    # Lost the race: someone else activated between our GET and SET. Put the
    # popped entry back where it was and serve whatever won.
    await redis.lpush(QUEUE_KEY, raw)
    current = await redis.get(ACTIVE_KEY)
    return PromotedSlot.model_validate_json(current) if current else None


async def stop_active(redis: Redis) -> bool:
    """Operator control: end the current run immediately. The next cards read
    advances the queue."""
    return bool(await redis.delete(ACTIVE_KEY))


async def enqueue(redis: Redis, promotion: QueuedPromotion) -> int:
    """Operator control: append a paid run to the queue. Returns queue length."""
    return await redis.rpush(QUEUE_KEY, promotion.model_dump_json(by_alias=True))


async def list_queue(redis: Redis) -> list[QueuedPromotion]:
    raws = await redis.lrange(QUEUE_KEY, 0, -1)
    return [QueuedPromotion.model_validate_json(r) for r in raws]


async def clear_queue(redis: Redis) -> int:
    return await redis.delete(QUEUE_KEY)
