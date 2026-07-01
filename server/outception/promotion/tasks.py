from typing import Any
from uuid import UUID

from outception.email.sender import (
    DEFAULT_FROM_EMAIL_ADDRESS,
    DEFAULT_FROM_NAME,
    DEFAULT_REPLY_TO_EMAIL_ADDRESS,
    DEFAULT_REPLY_TO_NAME,
)
from outception.integrations.tinybird import tinybird_client
from outception.models import User
from outception.worker import (
    AsyncSessionMaker,
    CronTrigger,
    TaskPriority,
    actor,
    enqueue_job,
)

from .events import PROMOTION_EVENTS_DATASOURCE
from .notifications import build_email
from .repository import PromotionRepository
from .service import promotion as promotion_service


@actor(actor_name="promotion.emit_events", priority=TaskPriority.LOW)
async def promotion_emit_events(events: list[dict[str, Any]]) -> None:
    await tinybird_client.send_events(PROMOTION_EVENTS_DATASOURCE, events)


@actor(
    actor_name="promotion.sweep",
    cron_trigger=CronTrigger(minute="*"),
    priority=TaskPriority.LOW,
    max_retries=0,
)
async def promotion_sweep() -> None:
    async with AsyncSessionMaker() as session:
        await promotion_service.sweep(session)


@actor(actor_name="promotion.send_lifecycle_email", priority=TaskPriority.LOW)
async def promotion_send_lifecycle_email(promotion_id: str, kind: str) -> None:
    async with AsyncSessionMaker() as session:
        promotion = await PromotionRepository.from_session(session).get_by_id(
            UUID(promotion_id)
        )
        if promotion is None:
            return
        author = await session.get(User, promotion.author_id)
        if author is None or not author.email:
            return
        if not author.promotion_emails_enabled:
            return

        position: int | None = None
        if kind == "queued":
            queue = await PromotionRepository.from_session(session).list_queue(
                promotion.category
            )
            ids = [p.id for p in queue]
            if promotion.id in ids:
                position = ids.index(promotion.id) + 1

        subject, html_content = build_email(promotion, kind, position=position)
        enqueue_job(
            "email.send",
            to_email_addr=author.email,
            subject=subject,
            html_content=html_content,
            from_name=DEFAULT_FROM_NAME,
            from_email_addr=DEFAULT_FROM_EMAIL_ADDRESS,
            email_headers=None,
            reply_to_name=DEFAULT_REPLY_TO_NAME,
            reply_to_email_addr=DEFAULT_REPLY_TO_EMAIL_ADDRESS,
            template=None,
            props_json=None,
        )
