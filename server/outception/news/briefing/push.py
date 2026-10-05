"""The morning push: one per subscribed profile per UTC day, carrying the
lead story of the latest briefing. Subscriptions are rows keyed by the
push endpoint or the device token; no account is involved."""

import asyncio
from datetime import UTC, date, datetime
from typing import Any

import structlog
from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from outception.config import settings
from outception.models import PushSubscription
from outception.postgres import AsyncSession
from outception.redis import Redis

from . import service
from .profiles import Profile
from .providers import Outcome, expo, web
from .schemas import BriefingResponse, PushSubscribe

log = structlog.get_logger()

# A row that fails this many mornings in a row is dropped.
MAX_FAILURES = 5
# Sends run in a small pool so a slow push service never stalls the worker.
CONCURRENCY = 8


async def subscribe(
    session: AsyncSession, profile: Profile, body: PushSubscribe
) -> None:
    keys = body.keys.model_dump() if body.keys else None
    statement = (
        pg_insert(PushSubscription)
        .values(
            profile_id=profile.id,
            kind=body.kind,
            endpoint=body.endpoint,
            keys=keys,
            failures=0,
        )
        .on_conflict_do_update(
            constraint="uq_push_subscription",
            set_={
                "kind": body.kind,
                "keys": keys,
                "failures": 0,
                "deleted_at": None,
                "modified_at": datetime.now(UTC),
            },
        )
    )
    await session.execute(statement)
    await session.flush()


async def unsubscribe(session: AsyncSession, profile: Profile, endpoint: str) -> None:
    await session.execute(
        delete(PushSubscription).where(
            PushSubscription.profile_id == profile.id,
            PushSubscription.endpoint == endpoint,
        )
    )
    await session.flush()


async def due(
    session: AsyncSession, profile: Profile, today: date
) -> list[PushSubscription]:
    """Rows that have not had today's briefing yet."""
    result = await session.execute(
        select(PushSubscription).where(
            PushSubscription.profile_id == profile.id,
            PushSubscription.deleted_at.is_(None),
            (PushSubscription.last_sent_for.is_(None))
            | (PushSubscription.last_sent_for < today),
        )
    )
    return list(result.scalars().all())


def message_for(profile: Profile, briefing: BriefingResponse) -> dict[str, Any] | None:
    """What the notification says: the lead story and how many more."""
    if not briefing.items:
        return None
    lead = briefing.items[0]
    rest = len(briefing.items) - 1
    body = lead.title if rest == 0 else f"{lead.title} and {rest} more"
    return {
        "title": f"{profile.id.replace('-', ' ').capitalize()} briefing",
        "body": body,
        "url": f"/briefing/{profile.id}",
        "profile": profile.id,
        "builtAt": briefing.built_at,
    }


async def deliver(row: PushSubscription, message: dict[str, Any]) -> Outcome:
    if row.kind == "web":
        return await asyncio.to_thread(web.send, row.endpoint, row.keys, message)
    return await expo.send(row.endpoint, message)


async def send_profile(
    session: AsyncSession, redis: Redis, profile: Profile, today: date | None = None
) -> dict[str, int]:
    """Push today's briefing to every row that has not had it. Returns the
    counts; a profile with no briefing yet sends nothing."""
    today = today or datetime.now(UTC).date()
    counts = {"delivered": 0, "gone": 0, "failed": 0}
    briefing = await service.latest(redis, profile)
    if briefing is None:
        return counts
    message = message_for(profile, briefing)
    if message is None:
        return counts
    rows = await due(session, profile, today)
    if not rows:
        return counts
    gate = asyncio.Semaphore(CONCURRENCY)

    async def one(row: PushSubscription) -> tuple[PushSubscription, Outcome]:
        async with gate:
            return row, await deliver(row, message)

    for row, outcome in await asyncio.gather(*(one(row) for row in rows)):
        counts[outcome] += 1
        if outcome == "delivered":
            await session.execute(
                update(PushSubscription)
                .where(PushSubscription.id == row.id)
                .values(last_sent_for=today, failures=0)
            )
        elif outcome == "gone" or row.failures + 1 >= MAX_FAILURES:
            await session.execute(
                delete(PushSubscription).where(PushSubscription.id == row.id)
            )
        else:
            await session.execute(
                update(PushSubscription)
                .where(PushSubscription.id == row.id)
                .values(failures=row.failures + 1)
            )
    await session.flush()
    log.info("push.sent", profile=profile.id, **counts)
    return counts


def public_key() -> str | None:
    """The VAPID public key the web client subscribes with; null until the
    keys are set, which hides the control."""
    return settings.WEB_PUSH_VAPID_PUBLIC_KEY if web.configured() else None
