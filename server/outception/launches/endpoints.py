"""Thin routes over the launch service. The archive, single reads, the
counting redirect and the view beacon are public; submit, edit, withdraw,
delete, mine and stats need a login (the owner); the review actions need
an address on the admin list."""

import hashlib
import json
from typing import Annotated, Literal
from uuid import UUID

from fastapi import Depends, Request, Response
from fastapi.responses import RedirectResponse

from outception.auth.dependencies import (
    WebUserOrAnonymous,
    WebUserRead,
    WebUserWrite,
)
from outception.auth.models import AuthSubject, is_user
from outception.exceptions import NotPermitted, ResourceNotFound
from outception.models import Launch, User
from outception.openapi import APITag
from outception.postgres import AsyncSession, get_db_session
from outception.redis import Redis, get_redis
from outception.routing import APIRouter
from outception.user.admin import is_admin
from outception.visits import service as visits
from outception.visits.schemas import Race

from . import service
from .schemas import (
    LaunchApprove,
    LaunchArchive,
    LaunchCreate,
    LaunchDay,
    LaunchEdit,
    LaunchMine,
    LaunchQueue,
    LaunchRead,
    LaunchReject,
    LaunchStats,
    LaunchUpdate,
    LaunchViews,
)

router = APIRouter(prefix="/launches", tags=["launches"])


def _read(launch: Launch) -> LaunchRead:
    return LaunchRead(
        id=launch.id,
        name=launch.name,
        tagline=launch.tagline,
        url=launch.url,
        logo=service.media_url(launch),
        kicker=launch.kicker,
        description=launch.description,
        state=launch.state,
        featured=launch.featured,
        day=launch.day,
        position=launch.position,
        created_at=launch.created_at,
    )


def _mine(launch: Launch, reach: tuple[int, int] = (0, 0)) -> LaunchMine:
    views, clicks = reach
    return LaunchMine(
        **_read(launch).model_dump(),
        reviewer_note=launch.reviewer_note,
        contact_email=launch.contact_email,
        views=views,
        clicks=clicks,
    )


async def _with_reach(
    session: AsyncSession, launches: list[Launch]
) -> list[LaunchMine]:
    reach = await service.totals(session, [launch.id for launch in launches])
    return [_mine(launch, reach.get(launch.id, (0, 0))) for launch in launches]


def _is_admin(auth_subject: AuthSubject[User]) -> bool:
    return is_admin(auth_subject.subject)


async def _admin(auth_subject: WebUserRead) -> AuthSubject[User]:
    if not _is_admin(auth_subject):
        raise NotPermitted()
    return auth_subject


AdminUser = Annotated[AuthSubject[User], Depends(_admin)]


@router.get("", response_model=LaunchArchive, tags=[APITag.public])
async def list_archive(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
) -> LaunchArchive | Response:
    """Every day's products, newest day first: the archive page."""
    days = [
        LaunchDay(day=day, items=[_read(launch) for launch in launches])
        for day, launches in await service.archive(session)
    ]
    body = LaunchArchive(days=days)
    encoded = json.dumps(body.model_dump(mode="json"), separators=(",", ":"))
    etag = f'"{hashlib.md5(encoded.encode()).hexdigest()[:20]}"'
    headers = {"Cache-Control": "public, max-age=60, s-maxage=60", "ETag": etag}
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers=headers)
    response.headers.update(headers)
    return body


@router.get("/mine", response_model=list[LaunchMine], tags=[APITag.private])
async def list_mine(
    auth_subject: WebUserRead, session: AsyncSession = Depends(get_db_session)
) -> list[LaunchMine]:
    """The reader's own submissions, newest first, with their reach."""
    return await _with_reach(
        session, list(await service.mine(session, auth_subject.subject))
    )


@router.get("/review", response_model=LaunchQueue, tags=[APITag.private])
async def review_queue(
    auth_subject: AdminUser, session: AsyncSession = Depends(get_db_session)
) -> LaunchQueue:
    """The founder's queue: submitted products, newest first, with the
    taken slots per day for the date picker."""
    return LaunchQueue(
        items=await _with_reach(session, list(await service.review_queue(session))),
        slots=await service.slots_taken(session),
    )


@router.post("/views", status_code=204, tags=[APITag.public])
async def record_views(
    body: LaunchViews, session: AsyncSession = Depends(get_db_session)
) -> None:
    """The wall showed these products: one view each. Unlisted ids are
    ignored, so the beacon reveals nothing."""
    await service.record_views(session, body.ids)


@router.get("/mine/race", response_model=Race, tags=[APITag.private])
async def my_race(
    auth_subject: WebUserRead, session: AsyncSession = Depends(get_db_session)
) -> Race:
    """The reader's products as a bar chart race, every day of the window."""
    return await service.race(session, auth_subject.subject.id)


@router.get("/visits/race", response_model=Race, tags=[APITag.private])
async def visits_race(
    auth_subject: AdminUser,
    dimension: Literal["path", "country"] = "path",
    session: AsyncSession = Depends(get_db_session),
) -> Race:
    """Site visits by page or by visitor country, for the admin list."""
    return await visits.race(session, dimension)


@router.get("/{id}", response_model=LaunchRead, tags=[APITag.public])
async def get_launch(
    id: UUID,
    auth_subject: WebUserOrAnonymous,
    session: AsyncSession = Depends(get_db_session),
) -> LaunchRead:
    """A listed product; before listing, only its submitter and the admin
    list can see it."""
    launch = await service.get(session, id)
    if launch.state not in service.VISIBLE:
        allowed = is_user(auth_subject) and (
            launch.user_id == auth_subject.subject.id or _is_admin(auth_subject)
        )
        if not allowed:
            raise ResourceNotFound("No such product")
    return _read(launch)


@router.get("/{id}/go", tags=[APITag.public])
async def go(
    id: UUID, session: AsyncSession = Depends(get_db_session)
) -> RedirectResponse:
    """Opens the product's link and counts the click."""
    launch = await service.record_click(session, id)
    response = RedirectResponse(launch.url, status_code=302)
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/{id}/stats", response_model=LaunchStats, tags=[APITag.private])
async def get_stats(
    id: UUID,
    auth_subject: WebUserRead,
    session: AsyncSession = Depends(get_db_session),
) -> LaunchStats:
    """The product's reach, for its submitter and the admin list."""
    launch = await service.get(session, id)
    if launch.user_id != auth_subject.subject.id and not _is_admin(auth_subject):
        raise NotPermitted()
    return await service.stats(session, id)


@router.post("", response_model=LaunchMine, status_code=201, tags=[APITag.private])
async def submit(
    body: LaunchCreate,
    auth_subject: WebUserWrite,
    session: AsyncSession = Depends(get_db_session),
) -> LaunchMine:
    return _mine(await service.submit(session, auth_subject.subject, body))


@router.patch("/{id}", response_model=LaunchMine, tags=[APITag.private])
async def update(
    id: UUID,
    body: LaunchUpdate,
    auth_subject: WebUserWrite,
    session: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> LaunchMine:
    """The submitter edits their own product."""
    return _mine(await service.update(session, redis, auth_subject.subject, id, body))


@router.post("/{id}/withdraw", status_code=204, tags=[APITag.private])
async def withdraw(
    id: UUID,
    auth_subject: WebUserWrite,
    session: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> None:
    """The submitter pulls their product out of the queue or off its day."""
    await service.withdraw(session, redis, auth_subject.subject, id)


@router.delete("/{id}", status_code=204, tags=[APITag.private])
async def delete(
    id: UUID,
    auth_subject: WebUserWrite,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """The submitter removes their product for good."""
    logo_path = await service.delete(session, auth_subject.subject, id)
    # The file goes only once the row is gone for sure.
    await session.commit()
    service.remove_logo_file(logo_path)


@router.post("/{id}/approve", response_model=LaunchMine, tags=[APITag.private])
async def approve(
    id: UUID,
    body: LaunchApprove,
    auth_subject: AdminUser,
    session: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> LaunchMine:
    return _mine(await service.approve(session, redis, id, body))


@router.post("/{id}/reject", response_model=LaunchMine, tags=[APITag.private])
async def reject(
    id: UUID,
    body: LaunchReject,
    auth_subject: AdminUser,
    session: AsyncSession = Depends(get_db_session),
) -> LaunchMine:
    return _mine(await service.reject(session, id, body.note))


@router.post("/{id}/edit", response_model=LaunchMine, tags=[APITag.private])
async def edit(
    id: UUID,
    body: LaunchEdit,
    auth_subject: AdminUser,
    session: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> LaunchMine:
    return _mine(await service.edit(session, redis, id, body))
