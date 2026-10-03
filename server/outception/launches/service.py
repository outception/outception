"""The state machine behind the Products of the day card, plus the card
itself: the day's five as news items with the house line first."""

import hashlib
import io
import json
from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import UUID

import structlog
from PIL import Image
from sqlalchemy import func, select

from outception.config import settings
from outception.email.sender import (
    DEFAULT_FROM_EMAIL_ADDRESS,
    DEFAULT_FROM_NAME,
    DEFAULT_REPLY_TO_EMAIL_ADDRESS,
    DEFAULT_REPLY_TO_NAME,
)
from outception.exceptions import BadRequest, NotPermitted, ResourceNotFound
from outception.kit.utils import utc_now
from outception.models import Launch, LaunchStatus, User
from outception.net.guard import is_fetchable_async
from outception.net.scrub import scrub
from outception.news import cache as news_cache
from outception.news.fetch import NewsFetchError, fetch_bytes
from outception.news.schemas import NewsExtra, NewsItem
from outception.postgres import AsyncSession
from outception.redis import Redis
from outception.worker import enqueue_job

from .schemas import SLOTS_PER_DAY, LaunchApprove, LaunchCreate, LaunchEdit

log = structlog.get_logger()

CARD_SOURCE_ID = "products-of-the-day"
# The card's items, as the source adapter reads them: written by every
# change here, so the adapter never needs the database on the request path.
CARD_ITEMS_KEY = "launches:card:items"
HOUSE_FILE = (
    Path(__file__).resolve().parent.parent / "news" / "data" / "house_launch.json"
)
BLOCKED_DOMAINS_FILE = HOUSE_FILE.parent / "blocked_domains.json"
LOGO_SIZE = 64
LOGO_MAX_BYTES = 2 * 1024 * 1024
VISIBLE = (LaunchStatus.live, LaunchStatus.ended)


def _domain(url: str) -> str:
    return url.split("//", 1)[-1].split("/", 1)[0].lower().removeprefix("www.")


def blocked_domains() -> frozenset[str]:
    try:
        raw = json.loads(BLOCKED_DOMAINS_FILE.read_text())
    except OSError, ValueError:
        return frozenset()
    return frozenset(str(item).lower() for item in raw if isinstance(item, str))


def favicon_url(url: str) -> str:
    domain = _domain(url)
    return (
        "https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON"
        f"&fallback_opts=TYPE,SIZE,URL&url=http://{domain}&size=128"
    )


def media_url(launch: Launch) -> str | None:
    if not launch.logo_path:
        return favicon_url(launch.url)
    return settings.generate_external_url(f"/media/{launch.logo_path}")


async def _store_logo(launch_id: UUID, logo_url: str) -> str | None:
    """Fetch the logo once through the guard, re-encode it to a small
    square and keep it on the media volume, so no remote image is ever
    hot-linked. None when anything about it is off."""
    if not await is_fetchable_async(logo_url):
        return None
    try:
        raw = await fetch_bytes(logo_url)
    except NewsFetchError:
        return None
    if len(raw) > LOGO_MAX_BYTES:
        return None
    try:
        image = Image.open(io.BytesIO(raw))
        image.thumbnail((LOGO_SIZE, LOGO_SIZE))
        square = Image.new("RGBA", (LOGO_SIZE, LOGO_SIZE), (0, 0, 0, 0))
        square.paste(
            image.convert("RGBA"),
            ((LOGO_SIZE - image.width) // 2, (LOGO_SIZE - image.height) // 2),
        )
    except Exception:
        return None
    relative = f"launches/{launch_id}.png"
    target = Path(settings.MEDIA_DIR) / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    square.save(target, format="PNG", optimize=True)
    return relative


def _notify(to: str, subject: str, html: str) -> None:
    try:
        enqueue_job(
            "email.send",
            to_email_addr=to,
            subject=subject,
            html_content=html,
            from_name=DEFAULT_FROM_NAME,
            from_email_addr=DEFAULT_FROM_EMAIL_ADDRESS,
            email_headers=None,
            reply_to_name=DEFAULT_REPLY_TO_NAME,
            reply_to_email_addr=DEFAULT_REPLY_TO_EMAIL_ADDRESS,
        )
    except RuntimeError:
        # No job queue bound (a bare script or test): the state change
        # still happened, the mail is the courtesy.
        log.info("launches.notify_skipped", to=to, subject=subject)


async def submit(session: AsyncSession, user: User, body: LaunchCreate) -> Launch:
    url = str(body.url)
    if _domain(url) in blocked_domains():
        raise BadRequest("That link cannot be listed")
    if not await is_fetchable_async(url):
        raise BadRequest("The link does not answer")
    try:
        await fetch_bytes(url)
    except NewsFetchError as e:
        raise BadRequest("The link does not answer") from e
    launch = Launch(
        user_id=user.id,
        name=scrub(body.name).strip(),
        tagline=scrub(body.tagline).strip(),
        url=url,
        kicker=body.kicker,
        description=scrub(body.description).strip(),
        contact_email=str(body.contact_email),
        state=LaunchStatus.submitted,
        day=body.preferred_day,
    )
    session.add(launch)
    await session.flush()
    if body.logo_url is not None:
        launch.logo_path = await _store_logo(launch.id, str(body.logo_url))
        await session.flush()
    for admin in settings.ADMIN_EMAILS:
        _notify(
            admin,
            f"New product submission: {launch.name}",
            f'<p>{launch.name}: {launch.tagline}</p><p><a href="{launch.url}">{launch.url}</a></p>'
            f"<p>Review it at {settings.generate_frontend_url('/account/review')}</p>",
        )
    return launch


async def get(session: AsyncSession, launch_id: UUID) -> Launch:
    launch = await session.get(Launch, launch_id)
    if launch is None:
        raise ResourceNotFound("No such product")
    return launch


async def mine(session: AsyncSession, user: User) -> Sequence[Launch]:
    result = await session.execute(
        select(Launch)
        .where(Launch.user_id == user.id)
        .order_by(Launch.created_at.desc())
    )
    return result.scalars().all()


async def withdraw(session: AsyncSession, user: User, launch_id: UUID) -> None:
    launch = await get(session, launch_id)
    if launch.user_id != user.id:
        raise NotPermitted()
    if launch.state != LaunchStatus.submitted:
        raise BadRequest("Only a submitted product can be withdrawn")
    launch.state = LaunchStatus.withdrawn
    await session.flush()


async def review_queue(session: AsyncSession) -> Sequence[Launch]:
    result = await session.execute(
        select(Launch)
        .where(Launch.state == LaunchStatus.submitted)
        .order_by(Launch.created_at.desc())
    )
    return result.scalars().all()


async def slots_taken(session: AsyncSession, days: int = 30) -> dict[str, int]:
    today = datetime.now(UTC).date()
    result = await session.execute(
        select(Launch.day, func.count())
        .where(
            Launch.state.in_((LaunchStatus.approved, LaunchStatus.live)),
            Launch.day >= today,
            Launch.day <= today + timedelta(days=days),
        )
        .group_by(Launch.day)
    )
    return {day.isoformat(): int(count) for day, count in result.all() if day}


async def approve(
    session: AsyncSession, redis: Redis, launch_id: UUID, body: LaunchApprove
) -> Launch:
    launch = await get(session, launch_id)
    if launch.state != LaunchStatus.submitted:
        raise BadRequest("Only a submitted product can be approved")
    taken = await session.execute(
        select(Launch.position).where(
            Launch.state.in_((LaunchStatus.approved, LaunchStatus.live)),
            Launch.day == body.day,
        )
    )
    positions = {int(p) for (p,) in taken.all() if p is not None}
    if len(positions) >= SLOTS_PER_DAY:
        raise BadRequest(
            f"{body.day.isoformat()} already has its {SLOTS_PER_DAY} products"
        )
    launch.position = next(p for p in range(1, SLOTS_PER_DAY + 1) if p not in positions)
    launch.day = body.day
    launch.featured = body.featured
    launch.reviewed_at = utc_now()
    launch.state = (
        LaunchStatus.live
        if body.day <= datetime.now(UTC).date()
        else LaunchStatus.approved
    )
    await session.flush()
    _notify(
        launch.contact_email,
        f"{launch.name} is in the Products of the day for {body.day.isoformat()}",
        f"<p>{launch.name} will show on {body.day.isoformat()}.</p>",
    )
    await rebuild_card(session, redis)
    return launch


async def reject(session: AsyncSession, launch_id: UUID, note: str) -> Launch:
    launch = await get(session, launch_id)
    if launch.state not in (LaunchStatus.submitted, LaunchStatus.approved):
        raise BadRequest("This product is past review")
    launch.state = LaunchStatus.rejected
    launch.reviewer_note = scrub(note).strip() or None
    launch.reviewed_at = utc_now()
    launch.day = None
    launch.position = None
    await session.flush()
    _notify(
        launch.contact_email,
        f"{launch.name} was not listed",
        f"<p>{launch.name} was not listed.</p>"
        + (f"<p>{launch.reviewer_note}</p>" if launch.reviewer_note else ""),
    )
    return launch


async def edit(
    session: AsyncSession, redis: Redis, launch_id: UUID, body: LaunchEdit
) -> Launch:
    launch = await get(session, launch_id)
    changed: list[str] = []
    for field in ("name", "tagline", "description", "kicker"):
        value = getattr(body, field)
        if value is not None:
            setattr(launch, field, scrub(value).strip() if field != "kicker" else value)
            changed.append(field)
    if changed:
        stamp = utc_now().strftime("%Y-%m-%d")
        line = f"Edited {', '.join(changed)} on {stamp}"
        launch.reviewer_note = (
            f"{launch.reviewer_note}\n{line}" if launch.reviewer_note else line
        )
        await session.flush()
        if launch.state in (LaunchStatus.approved, LaunchStatus.live):
            await rebuild_card(session, redis)
    return launch


async def rotate_day(
    session: AsyncSession, redis: Redis, today: date | None = None
) -> dict[str, int]:
    """At midnight: the day's approved products go live, yesterday's live
    ones end, and the card is rebuilt."""
    today = today or datetime.now(UTC).date()
    result = await session.execute(
        select(Launch).where(
            Launch.state.in_((LaunchStatus.approved, LaunchStatus.live)),
            Launch.day.is_not(None),
        )
    )
    counts = {"live": 0, "ended": 0}
    for launch in result.scalars().all():
        assert launch.day is not None
        if launch.state == LaunchStatus.approved and launch.day <= today:
            launch.state = LaunchStatus.live
            counts["live"] += 1
        elif launch.state == LaunchStatus.live and launch.day < today:
            launch.state = LaunchStatus.ended
            counts["ended"] += 1
    await session.flush()
    await rebuild_card(session, redis, today=today)
    return counts


async def archive(
    session: AsyncSession, days: int = 30
) -> list[tuple[date, list[Launch]]]:
    today = datetime.now(UTC).date()
    result = await session.execute(
        select(Launch)
        .where(Launch.state.in_(VISIBLE), Launch.day >= today - timedelta(days=days))
        .order_by(Launch.day.desc(), Launch.featured.desc(), Launch.position)
    )
    grouped: dict[date, list[Launch]] = {}
    for launch in result.scalars().all():
        assert launch.day is not None
        grouped.setdefault(launch.day, []).append(launch)
    return list(grouped.items())


def house_item(day: date) -> NewsItem:
    raw = json.loads(HOUSE_FILE.read_text())
    return NewsItem(
        id=f"house-{day.isoformat()}",
        title=f"{raw['name']}: {raw['tagline']}",
        url=str(raw["url"]),
        pub_date=int(
            datetime(day.year, day.month, day.day, tzinfo=UTC).timestamp() * 1000
        ),
        extra=NewsExtra(
            hover=str(raw.get("kicker") or "house"),
            info=str(raw.get("info") or ""),
            icon=str(raw.get("icon") or "") or None,
        ),
    )


def _item(launch: Launch) -> NewsItem:
    assert launch.day is not None
    day = launch.day
    return NewsItem(
        id=f"launch-{launch.id}",
        title=f"{launch.name}: {launch.tagline}",
        url=launch.url,
        pub_date=int(
            datetime(day.year, day.month, day.day, tzinfo=UTC).timestamp() * 1000
        ),
        extra=NewsExtra(
            hover="featured" if launch.featured else launch.kicker,
            info=launch.description or None,
            icon=media_url(launch),
        ),
    )


async def card_items(
    session: AsyncSession, today: date | None = None
) -> list[NewsItem]:
    """The house line, then today's five (featured second), then
    yesterday's under the fold. Never padded."""
    today = today or datetime.now(UTC).date()
    result = await session.execute(
        select(Launch)
        .where(
            Launch.state.in_((LaunchStatus.live, LaunchStatus.ended)),
            Launch.day >= today - timedelta(days=1),
            Launch.day <= today,
        )
        .order_by(Launch.day.desc(), Launch.featured.desc(), Launch.position)
    )
    items = [house_item(today)]
    items.extend(_item(launch) for launch in result.scalars().all())
    return items


async def rebuild_card(
    session: AsyncSession, redis: Redis, today: date | None = None
) -> None:
    items = await card_items(session, today)
    payload = json.dumps([item.model_dump(by_alias=True) for item in items])
    await redis.set(CARD_ITEMS_KEY, payload)
    await news_cache.set(redis, CARD_SOURCE_ID, items)


def sender_hash(value: str) -> str:
    return hashlib.blake2b(value.encode(), digest_size=16).hexdigest()
