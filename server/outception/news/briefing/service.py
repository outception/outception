"""What the routes read: the latest briefing from Redis, history from
Postgres, the profile list, and a signed-in reader's chosen profiles in
their prefs."""

import json
from datetime import timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from outception.kit.utils import generate_uuid, utc_now
from outception.models import NewsBriefing, ReaderPref
from outception.postgres import AsyncSession
from outception.redis import Redis

from .builder import LATEST_KEY, STALE_AFTER_MS
from .profiles import Profile, profiles
from .schemas import (
    BriefingDay,
    BriefingHistoryResponse,
    BriefingProfile,
    BriefingProfilesResponse,
    BriefingResponse,
)

PREF_KEY = "briefing_profiles"


def profile_list() -> BriefingProfilesResponse:
    from . import push

    return BriefingProfilesResponse(
        push_public_key=push.public_key(),
        profiles=[
            BriefingProfile(
                id=p.id, template=p.template, categories=list(p.category_ids)
            )
            for p in profiles().values()
        ],
    )


def get_profile(profile_id: str) -> Profile | None:
    return profiles().get(profile_id)


async def latest(redis: Redis, profile: Profile) -> BriefingResponse | None:
    raw = await redis.get(LATEST_KEY.format(profile=profile.id))
    if raw is None:
        return None
    try:
        payload: dict[str, Any] = json.loads(raw)
    except ValueError:
        return None
    built_at = int(payload.get("builtAt") or 0)
    age_ms = int(utc_now().timestamp() * 1000) - built_at
    return BriefingResponse.model_validate(
        {
            "status": "success" if age_ms < STALE_AFTER_MS else "cache",
            "profile": profile.id,
            "builtAt": built_at,
            "staleAfterMs": int(payload.get("staleAfterMs") or STALE_AFTER_MS),
            "items": payload.get("items") or [],
        }
    )


async def history(
    session: AsyncSession, profile: Profile, days: int
) -> BriefingHistoryResponse:
    since = utc_now() - timedelta(days=days)
    result = await session.execute(
        select(NewsBriefing)
        .where(NewsBriefing.profile_id == profile.id, NewsBriefing.built_at >= since)
        .order_by(NewsBriefing.built_at.desc())
    )
    latest_per_day: dict[str, NewsBriefing] = {}
    for row in result.scalars().all():
        latest_per_day.setdefault(row.built_for.isoformat(), row)
    return BriefingHistoryResponse(
        profile=profile.id,
        days=[
            BriefingDay.model_validate(
                {
                    "builtFor": row.built_for,
                    "builtAt": int(row.built_at.timestamp() * 1000),
                    "items": row.items,
                }
            )
            for row in latest_per_day.values()
        ],
    )


async def mine(session: AsyncSession, user_id: UUID) -> list[str]:
    value = await session.scalar(
        select(ReaderPref.value).where(
            ReaderPref.user_id == user_id, ReaderPref.key == PREF_KEY
        )
    )
    if not isinstance(value, list):
        return []
    return [str(v) for v in value if str(v) in profiles()]


async def _save(session: AsyncSession, user_id: UUID, chosen: list[str]) -> None:
    statement = (
        pg_insert(ReaderPref)
        .values(
            id=generate_uuid(),
            created_at=utc_now(),
            user_id=user_id,
            key=PREF_KEY,
            value=chosen,
        )
        .on_conflict_do_update(
            constraint="uq_reader_pref",
            set_={"value": chosen, "modified_at": utc_now()},
        )
    )
    await session.execute(statement)


async def choose(session: AsyncSession, user_id: UUID, profile_id: str) -> list[str]:
    chosen = await mine(session, user_id)
    if profile_id not in chosen:
        chosen.append(profile_id)
        await _save(session, user_id, chosen)
    return chosen


async def drop(session: AsyncSession, user_id: UUID, profile_id: str) -> list[str]:
    chosen = await mine(session, user_id)
    if profile_id in chosen:
        chosen.remove(profile_id)
        await _save(session, user_id, chosen)
    return chosen
