"""The briefing routes. `/profiles` and `/me` are declared before
`/{profile}` on purpose."""

from fastapi import Depends, Query, Request, Response

from outception.auth.dependencies import WebUserRead, WebUserWrite
from outception.exceptions import ResourceNotFound
from outception.openapi import APITag
from outception.postgres import AsyncSession, get_db_session
from outception.redis import Redis, get_redis
from outception.routing import APIRouter

from . import push, service
from .profiles import Profile
from .schemas import (
    BriefingHistoryResponse,
    BriefingMine,
    BriefingProfilesResponse,
    BriefingResponse,
    PushSubscribe,
    PushUnsubscribe,
)

router = APIRouter(prefix="/briefing", tags=["briefing"])


def _profile(profile_id: str) -> Profile:
    profile = service.get_profile(profile_id)
    if profile is None:
        raise ResourceNotFound(f"Unknown profile: {profile_id}")
    return profile


@router.get("/profiles", response_model=BriefingProfilesResponse, tags=[APITag.public])
async def list_profiles(response: Response) -> BriefingProfilesResponse:
    """Profile ids and their categories; names are client i18n keyed by id."""
    response.headers["Cache-Control"] = "public, max-age=600, s-maxage=3600"
    response.headers["Vary"] = "Origin"
    return service.profile_list()


@router.get("/me", response_model=BriefingMine, tags=[APITag.private])
async def my_profiles(
    auth_subject: WebUserRead, session: AsyncSession = Depends(get_db_session)
) -> BriefingMine:
    return BriefingMine(profiles=await service.mine(session, auth_subject.subject.id))


@router.put("/me/{profile}", status_code=204, tags=[APITag.private])
async def choose_profile(
    profile: str,
    auth_subject: WebUserWrite,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    _profile(profile)
    await service.choose(session, auth_subject.subject.id, profile)


@router.delete("/me/{profile}", status_code=204, tags=[APITag.private])
async def drop_profile(
    profile: str,
    auth_subject: WebUserWrite,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    await service.drop(session, auth_subject.subject.id, profile)


@router.get("/{profile}", response_model=BriefingResponse, tags=[APITag.public])
async def get_briefing(
    profile: str,
    request: Request,
    response: Response,
    redis: Redis = Depends(get_redis),
) -> BriefingResponse | Response:
    """The latest briefing for a profile, read from Redis only."""
    briefing = await service.latest(redis, _profile(profile))
    if briefing is None:
        raise ResourceNotFound(f"No briefing built yet for {profile}")
    etag = f'"{briefing.built_at}"'
    headers = {
        "Cache-Control": "public, max-age=60, s-maxage=300",
        "Vary": "Origin",
        "ETag": etag,
    }
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers=headers)
    response.headers.update(headers)
    return briefing


@router.get(
    "/{profile}/history", response_model=BriefingHistoryResponse, tags=[APITag.public]
)
async def get_history(
    profile: str,
    response: Response,
    days: int = Query(7, ge=1, le=90),
    session: AsyncSession = Depends(get_db_session),
) -> BriefingHistoryResponse:
    response.headers["Cache-Control"] = "public, max-age=300, s-maxage=900"
    response.headers["Vary"] = "Origin"
    return await service.history(session, _profile(profile), days)


@router.post("/{profile}/subscribe", status_code=204, tags=[APITag.public])
async def subscribe_push(
    profile: str,
    body: PushSubscribe,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    """Ask for one push a day with this profile's briefing. No account; the
    endpoint or device token is the only identity. Sending it again
    refreshes the row."""
    await push.subscribe(session, _profile(profile), body)
    return Response(status_code=204, headers={"Cache-Control": "no-store"})


@router.delete("/{profile}/subscribe", status_code=204, tags=[APITag.public])
async def unsubscribe_push(
    profile: str,
    body: PushUnsubscribe,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    """Stop the morning push for this device and profile."""
    await push.unsubscribe(session, _profile(profile), body.endpoint)
    return Response(status_code=204, headers={"Cache-Control": "no-store"})
