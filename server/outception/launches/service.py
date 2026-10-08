"""The state machine behind the Products of the day card, plus the card
itself: the day's five as news items with the house line first."""

import asyncio
import hashlib
import html
import io
import json
import os
import re
import tempfile
from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID

import structlog
from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from outception.config import settings
from outception.email.sender import (
    DEFAULT_FROM_EMAIL_ADDRESS,
    DEFAULT_FROM_NAME,
    DEFAULT_REPLY_TO_EMAIL_ADDRESS,
    DEFAULT_REPLY_TO_NAME,
)
from outception.exceptions import BadRequest, NotPermitted, ResourceNotFound
from outception.kit.utils import utc_now
from outception.models import Launch, LaunchMetric, LaunchStatus, User
from outception.net.guard import is_fetchable_async
from outception.net.scrub import scrub
from outception.news import cache as news_cache
from outception.news.fetch import FETCH_TIMEOUT_SECONDS, NewsFetchError, fetch_bytes
from outception.news.schemas import NewsExtra, NewsItem
from outception.postgres import AsyncSession
from outception.redis import Redis
from outception.visits.schemas import Race
from outception.visits.series import zero_fill
from outception.worker import enqueue_job

from .schemas import (
    SLOTS_PER_DAY,
    LaunchApprove,
    LaunchCreate,
    LaunchEdit,
    LaunchStatDay,
    LaunchStats,
    LaunchUpdate,
)

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
# The submitter may edit while nothing is listed, and delete anything that is
# not on a day; a listed product is withdrawn first.
EDITABLE = (LaunchStatus.submitted, LaunchStatus.withdrawn, LaunchStatus.rejected)
LISTED = (LaunchStatus.approved, LaunchStatus.live)


def _domain(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    return host.removeprefix("www.")


def _blocked(url: str) -> bool:
    """Blocked by the domain or any parent: userinfo, ports and subdomains
    do not slip past the list."""
    host = _domain(url)
    return any(
        host == blocked or host.endswith("." + blocked) for blocked in blocked_domains()
    )


# Pillow's own bomb threshold is far above what a logo needs; a 2 MB PNG can
# still decode to hundreds of megabytes, so the pixel count is capped first
# (a 2048 square decodes to 16 MB), and two decodes run at a time at most:
# a handful of edits in parallel must not add up to the API's memory.
LOGO_MAX_PIXELS = 2048 * 2048
_DECODES = asyncio.Semaphore(2)


def _decode_logo(raw: bytes) -> Image.Image | None:
    try:
        image = Image.open(io.BytesIO(raw))
        if image.width * image.height > LOGO_MAX_PIXELS:
            return None
        # A JPEG can decode at a fraction of its size when that is all we
        # keep; other formats ignore the hint.
        image.draft("RGB", (LOGO_SIZE * 4, LOGO_SIZE * 4))
        image.thumbnail((LOGO_SIZE, LOGO_SIZE))
        square = Image.new("RGBA", (LOGO_SIZE, LOGO_SIZE), (0, 0, 0, 0))
        square.paste(
            image.convert("RGBA"),
            ((LOGO_SIZE - image.width) // 2, (LOGO_SIZE - image.height) // 2),
        )
    except Exception:
        return None
    return square


def _save_logo(square: Image.Image, target: Path) -> None:
    """Write beside the target, then swap it in: a failed or half-written
    save never replaces the logo that is there, and nobody ever reads a
    half-written file."""
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    try:
        with os.fdopen(handle, "wb") as file:
            square.save(file, format="PNG", optimize=True)
        os.chmod(temporary, 0o644)
        os.replace(temporary, target)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


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
    try:
        async with asyncio.timeout(FETCH_TIMEOUT_SECONDS):
            if not await is_fetchable_async(logo_url):
                return None
            raw = await fetch_bytes(logo_url)
    except NewsFetchError, TimeoutError:
        return None
    if len(raw) > LOGO_MAX_BYTES:
        return None
    # The decode runs off the event loop: a slow image must not stall the API.
    async with _DECODES:
        square = await asyncio.to_thread(_decode_logo, raw)
    if square is None:
        return None
    relative = f"launches/{launch_id}.png"
    try:
        await asyncio.to_thread(_save_logo, square, Path(settings.MEDIA_DIR) / relative)
    except OSError:
        log.info("launches.logo_save_failed", path=relative)
        return None
    return relative


def remove_logo_file(logo_path: str | None) -> None:
    """Delete a stored logo. Called once the row that named it is
    committed away, never before."""
    if not logo_path:
        return
    try:
        (Path(settings.MEDIA_DIR) / logo_path).unlink(missing_ok=True)
    except OSError:
        log.info("launches.logo_unlink_failed", path=logo_path)


def _h(value: object) -> str:
    """User text on its way into HTML mail."""
    return html.escape(str(value), quote=True)


def _subject(text: str) -> str:
    """A header line: no line breaks, which the SMTP sender rejects."""
    return re.sub(r"\s+", " ", text).strip()[:200]


def _notify(to: str, subject: str, html: str) -> None:
    try:
        enqueue_job(
            "email.send",
            to_email_addr=to,
            subject=_subject(subject),
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


def _notify_admins(subject: str, html: str) -> None:
    for admin in settings.ADMIN_EMAILS:
        _notify(admin, subject, html)


def _review_link() -> str:
    return f"<p>Review it at {settings.generate_frontend_url('/account/review')}</p>"


def _details(launch: Launch, user: User | None = None) -> str:
    """The product as the founder needs it in the mail: name, line, link,
    kind, who sent it and how to reach them."""
    rows = [
        ("Product", _h(launch.name)),
        ("Tagline", _h(launch.tagline)),
        ("Link", f'<a href="{_h(launch.url)}">{_h(launch.url)}</a>'),
        ("Kind", _h(launch.kicker)),
        ("Description", _h(launch.description or "(none)")),
        ("Contact", _h(launch.contact_email)),
        ("Submitted by", _h(user.email) if user is not None else "the submitter"),
        ("State", _h(launch.state)),
        ("Preferred day", launch.day.isoformat() if launch.day else "(none)"),
    ]
    return "<ul>" + "".join(f"<li>{k}: {v}</li>" for k, v in rows) + "</ul>"


async def _check_link(url: str) -> None:
    if _blocked(url):
        raise BadRequest("That link cannot be listed")
    try:
        async with asyncio.timeout(FETCH_TIMEOUT_SECONDS):
            if not await is_fetchable_async(url):
                raise BadRequest("The link does not answer")
            await fetch_bytes(url)
    except (NewsFetchError, TimeoutError) as e:
        raise BadRequest("The link does not answer") from e


async def submit(session: AsyncSession, user: User, body: LaunchCreate) -> Launch:
    url = str(body.url)
    await _check_link(url)
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
    _notify_admins(
        f"New product submission: {launch.name}",
        f"<p>{user.email} submitted a product.</p>"
        + _details(launch, user)
        + _review_link(),
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


async def _owned(session: AsyncSession, user: User, launch_id: UUID) -> Launch:
    launch = await get(session, launch_id)
    if launch.user_id != user.id:
        raise NotPermitted()
    return launch


async def withdraw(
    session: AsyncSession, redis: Redis, user: User, launch_id: UUID
) -> None:
    """The submitter pulls a product out of the queue, or off a day it has
    not reached yet; the slot frees and the founder hears about it."""
    launch = await _owned(session, user, launch_id)
    if launch.state not in (LaunchStatus.submitted, LaunchStatus.approved):
        raise BadRequest("Only a waiting or approved product can be withdrawn")
    was_approved = launch.state == LaunchStatus.approved
    launch.state = LaunchStatus.withdrawn
    launch.day = None
    launch.position = None
    await session.flush()
    if was_approved:
        await rebuild_card(session, redis)
    _notify_admins(
        f"Product withdrawn: {launch.name}",
        f"<p>{_h(user.email)} withdrew their product"
        + (" from its approved day" if was_approved else " from the queue")
        + ".</p>"
        + _details(launch, user),
    )


async def update(
    session: AsyncSession,
    redis: Redis,
    user: User,
    launch_id: UUID,
    body: LaunchUpdate,
) -> Launch:
    """The submitter edits their own product. Allowed while nothing is
    listed; a withdrawn or rejected product goes back into the queue."""
    launch = await _owned(session, user, launch_id)
    if launch.state not in EDITABLE:
        raise BadRequest("Withdraw the product before editing it")
    before = (
        launch.name,
        launch.tagline,
        launch.url,
        launch.description,
        launch.kicker,
        launch.logo_path,
        launch.contact_email,
        launch.day,
    )
    if body.url is not None and str(body.url) != launch.url:
        await _check_link(str(body.url))
        launch.url = str(body.url)
    for field in ("name", "tagline", "description"):
        value = getattr(body, field)
        if value is not None:
            setattr(launch, field, scrub(value).strip())
    if body.kicker is not None:
        launch.kicker = body.kicker
    if body.contact_email is not None:
        launch.contact_email = str(body.contact_email)
    if body.preferred_day is not None:
        launch.day = body.preferred_day
    logo_changed = False
    if body.logo_url is not None:
        # The stored name is the same for every logo of a product, so a new
        # logo is told by the fetch succeeding; a failed fetch keeps the old.
        stored = await _store_logo(launch.id, str(body.logo_url))
        if stored is not None:
            launch.logo_path = stored
            logo_changed = True
    resubmitted = launch.state != LaunchStatus.submitted
    if resubmitted:
        launch.state = LaunchStatus.submitted
        launch.reviewer_note = None
        launch.reviewed_at = None
        launch.position = None
    await session.flush()
    changed = before != (
        launch.name,
        launch.tagline,
        launch.url,
        launch.description,
        launch.kicker,
        launch.logo_path,
        launch.contact_email,
        launch.day,
    )
    # The founder hears about a resubmission or a changed listing, not about
    # a saved form with nothing new in it.
    if resubmitted or changed or logo_changed:
        _notify_admins(
            f"Product {'resubmitted' if resubmitted else 'updated'}: {launch.name}",
            f"<p>{_h(user.email)} {'resubmitted' if resubmitted else 'updated'} their product.</p>"
            + _details(launch, user)
            + _review_link(),
        )
    return launch


async def delete(session: AsyncSession, user: User, launch_id: UUID) -> str | None:
    """The submitter removes a product for good, with its reach; a product
    on a day is withdrawn first. Returns the stored logo, for the caller to
    remove once the deletion is committed."""
    launch = await _owned(session, user, launch_id)
    if launch.state in LISTED:
        raise BadRequest("Withdraw the product before deleting it")
    logo_path = launch.logo_path
    await session.delete(launch)
    await session.flush()
    return logo_path


async def record_views(session: AsyncSession, ids: Sequence[UUID]) -> int:
    """The wall showed these products: one view each, today. Only listed
    products count, so a guessed id changes nothing."""
    today = datetime.now(UTC).date()
    listed = await session.execute(
        select(Launch.id).where(Launch.id.in_(set(ids)), Launch.state.in_(VISIBLE))
    )
    counted = 0
    for (launch_id,) in listed.all():
        await _bump(session, launch_id, today, views=1)
        counted += 1
    return counted


async def record_click(session: AsyncSession, launch_id: UUID) -> Launch:
    """A reader opened the product's link: one click, today."""
    launch = await get(session, launch_id)
    if launch.state not in VISIBLE:
        raise ResourceNotFound("No such product")
    await _bump(session, launch.id, datetime.now(UTC).date(), clicks=1)
    return launch


async def _bump(
    session: AsyncSession,
    launch_id: UUID,
    day: date,
    *,
    views: int = 0,
    clicks: int = 0,
) -> None:
    statement = pg_insert(LaunchMetric).values(
        launch_id=launch_id, day=day, views=views, clicks=clicks
    )
    await session.execute(
        statement.on_conflict_do_update(
            index_elements=["launch_id", "day"],
            set_={
                "views": LaunchMetric.views + statement.excluded.views,
                "clicks": LaunchMetric.clicks + statement.excluded.clicks,
            },
        )
    )


async def totals(
    session: AsyncSession, ids: Sequence[UUID]
) -> dict[UUID, tuple[int, int]]:
    """Views and clicks per product, summed over its days."""
    if not ids:
        return {}
    result = await session.execute(
        select(
            LaunchMetric.launch_id,
            func.coalesce(func.sum(LaunchMetric.views), 0),
            func.coalesce(func.sum(LaunchMetric.clicks), 0),
        )
        .where(LaunchMetric.launch_id.in_(list(ids)))
        .group_by(LaunchMetric.launch_id)
    )
    return {row[0]: (int(row[1]), int(row[2])) for row in result.all()}


async def stats(session: AsyncSession, launch_id: UUID, days: int = 30) -> LaunchStats:
    summed = await totals(session, [launch_id])
    views, clicks = summed.get(launch_id, (0, 0))
    since = datetime.now(UTC).date() - timedelta(days=days)
    rows = await session.execute(
        select(LaunchMetric.day, LaunchMetric.views, LaunchMetric.clicks)
        .where(LaunchMetric.launch_id == launch_id, LaunchMetric.day >= since)
        .order_by(LaunchMetric.day.desc())
    )
    return LaunchStats(
        views=views,
        clicks=clicks,
        days=[LaunchStatDay(day=d, views=v, clicks=c) for d, v, c in rows.all()],
    )


def distinct_labels(names: Sequence[str]) -> list[str]:
    """One label per name, in order. Two products with one name get a
    visible suffix, "Name (2)", and a number another product already has
    as its real name is skipped, so no two bars ever share a label."""
    used: set[str] = set()
    labels: list[str] = []
    for name in names:
        label, n = name, 1
        while label in used:
            n += 1
            label = f"{name} ({n})"
        used.add(label)
        labels.append(label)
    return labels


async def race(session: AsyncSession, user_id: UUID, days: int = 30) -> Race:
    """The submitter's reach as a bar chart race. Two or more products race
    each other by daily views (the client makes them cumulative); a single
    product races its views against its clicks."""
    today = datetime.now(UTC).date()
    since = today - timedelta(days=days)
    owned = await session.execute(
        select(Launch.id, Launch.name)
        .where(Launch.user_id == user_id, Launch.deleted_at.is_(None))
        .order_by(Launch.created_at.asc())
    )
    launches = owned.all()
    if not launches:
        return Race(mode="products", rows=[])
    names: dict[UUID, str] = dict(
        zip(
            (launch_id for launch_id, _ in launches),
            distinct_labels([name for _, name in launches]),
            strict=True,
        )
    )
    metrics = await session.execute(
        select(
            LaunchMetric.launch_id,
            LaunchMetric.day,
            LaunchMetric.views,
            LaunchMetric.clicks,
        ).where(LaunchMetric.launch_id.in_(list(names)), LaunchMetric.day >= since)
    )
    rows = metrics.all()
    if not rows:
        # No reach yet: an empty race, so the page says so instead of
        # animating a month of empty bars.
        return Race(mode="reach" if len(names) == 1 else "products", rows=[])
    if len(names) == 1:
        points = {}
        for _, day, views, clicks in rows:
            points[(day, "views")] = int(views)
            points[(day, "clicks")] = int(clicks)
        return Race(
            mode="reach", rows=zero_fill(points, ("views", "clicks"), since, today)
        )
    points = {(day, names[launch_id]): int(views) for launch_id, day, views, _ in rows}
    return Race(mode="products", rows=zero_fill(points, names.values(), since, today))


def go_url(launch: Launch) -> str:
    """The counting redirect every listing opens the product through."""
    return settings.generate_external_url(f"/v1/launches/{launch.id}/go")


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
        f"<p>{_h(launch.name)} will show on {body.day.isoformat()}.</p>",
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
        f"<p>{_h(launch.name)} was not listed.</p>"
        + (f"<p>{_h(launch.reviewer_note)}</p>" if launch.reviewer_note else ""),
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
        url=go_url(launch),
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
