"""Thin routes over the launch service. The archive and single reads are
public; submit, withdraw and mine need a login; the review actions need
an address on the admin list."""

import hashlib
import json
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request, Response

from outception.auth.dependencies import WebUserRead, WebUserWrite
from outception.auth.models import AuthSubject
from outception.config import settings
from outception.exceptions import NotPermitted, ResourceNotFound
from outception.models import Launch, User
from outception.openapi import APITag
from outception.postgres import AsyncSession, get_db_session
from outception.redis import Redis, get_redis
from outception.routing import APIRouter

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


def _mine(launch: Launch) -> LaunchMine:
    return LaunchMine(
        **_read(launch).model_dump(),
        reviewer_note=launch.reviewer_note,
        contact_email=launch.contact_email,
    )


async def _admin(auth_subject: WebUserRead) -> AuthSubject[User]:
    if auth_subject.subject.email not in settings.ADMIN_EMAILS:
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
    return [
        _mine(launch) for launch in await service.mine(session, auth_subject.subject)
    ]


@router.get("/review", response_model=LaunchQueue, tags=[APITag.private])
async def review_queue(
    auth_subject: AdminUser, session: AsyncSession = Depends(get_db_session)
) -> LaunchQueue:
    """The founder's queue: submitted products, newest first, with the
    taken slots per day for the date picker."""
    return LaunchQueue(
        items=[_mine(launch) for launch in await service.review_queue(session)],
        slots=await service.slots_taken(session),
    )


@router.get("/{id}", response_model=LaunchRead, tags=[APITag.public])
async def get_launch(
    id: UUID, session: AsyncSession = Depends(get_db_session)
) -> LaunchRead:
    launch = await service.get(session, id)
    if launch.state not in service.VISIBLE:
        raise ResourceNotFound("No such product")
    return _read(launch)


@router.post("", response_model=LaunchMine, status_code=201, tags=[APITag.private])
async def submit(
    body: LaunchCreate,
    auth_subject: WebUserWrite,
    session: AsyncSession = Depends(get_db_session),
) -> LaunchMine:
    return _mine(await service.submit(session, auth_subject.subject, body))


@router.delete("/{id}", status_code=204, tags=[APITag.private])
async def withdraw(
    id: UUID,
    auth_subject: WebUserWrite,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    await service.withdraw(session, auth_subject.subject, id)


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
