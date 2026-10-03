import hashlib
from datetime import UTC, datetime

from sqlalchemy import func, select, update

from outception.config import settings
from outception.email.sender import (
    DEFAULT_FROM_EMAIL_ADDRESS,
    DEFAULT_FROM_NAME,
    DEFAULT_REPLY_TO_EMAIL_ADDRESS,
    DEFAULT_REPLY_TO_NAME,
)
from outception.models import Feedback, Launch, LaunchStatus
from outception.net.scrub import scrub
from outception.postgres import AsyncSession
from outception.worker import enqueue_job

from .schemas import FeedbackCreate

CONTEXT_VALUE_CHARS = 200


def sender_hash(address: str | None) -> str | None:
    if not address:
        return None
    return hashlib.blake2b(
        address.encode(), key=settings.SECRET.encode()[:64], digest_size=16
    ).hexdigest()


def _small_context(context: dict[str, object] | None) -> dict[str, object] | None:
    if not context:
        return None
    return {
        str(k)[:32]: scrub(str(v))[:CONTEXT_VALUE_CHARS] for k, v in context.items()
    }


async def submit(
    session: AsyncSession, body: FeedbackCreate, *, ip: str | None
) -> Feedback:
    feedback = Feedback(
        message=scrub(body.message).strip(),
        email=str(body.email) if body.email else None,
        surface=body.surface,
        context=_small_context(body.context),
        sender_hash=sender_hash(ip),
    )
    session.add(feedback)
    await session.flush()
    return feedback


async def pending(session: AsyncSession) -> list[Feedback]:
    result = await session.execute(
        select(Feedback)
        .where(Feedback.digested.is_(False))
        .order_by(Feedback.created_at)
    )
    return list(result.scalars().all())


async def waiting_submissions(session: AsyncSession) -> int:
    return int(
        await session.scalar(
            select(func.count())
            .select_from(Launch)
            .where(Launch.state == LaunchStatus.submitted)
        )
        or 0
    )


def digest_html(items: list[Feedback], waiting: int) -> str:
    lines = [
        f"<p>{len(items)} new message(s); {waiting} product submission(s) waiting.</p>"
    ]
    if waiting:
        lines.append(
            f'<p><a href="{settings.generate_frontend_url("/account/review")}">Review the queue</a></p>'
        )
    for item in items:
        when = item.created_at.astimezone(UTC).strftime("%Y-%m-%d %H:%M")
        who = item.email or "no address"
        lines.append(
            f"<hr><p><b>{when}</b> · {item.surface} · {who}</p><p>{item.message}</p>"
        )
    return "\n".join(lines)


async def send_digest(session: AsyncSession) -> int:
    """The daily digest to the configured address: every undigested
    message plus the waiting submission count. Returns how many it
    carried; nothing is sent when there is nothing to say."""
    items = await pending(session)
    waiting = await waiting_submissions(session)
    to = settings.FEEDBACK_DIGEST_EMAIL
    if not to or (not items and not waiting):
        return 0
    enqueue_job(
        "email.send",
        to_email_addr=to,
        subject=f"Outception digest: {len(items)} message(s), {waiting} waiting",
        html_content=digest_html(items, waiting),
        from_name=DEFAULT_FROM_NAME,
        from_email_addr=DEFAULT_FROM_EMAIL_ADDRESS,
        email_headers=None,
        reply_to_name=DEFAULT_REPLY_TO_NAME,
        reply_to_email_addr=DEFAULT_REPLY_TO_EMAIL_ADDRESS,
    )
    if items:
        await session.execute(
            update(Feedback)
            .where(Feedback.id.in_([item.id for item in items]))
            .values(digested=True, modified_at=datetime.now(UTC))
        )
        await session.flush()
    return len(items)
