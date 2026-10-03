import json
from typing import Annotated, Any

import structlog

from outception.config import settings
from outception.kit.utils import utc_now
from outception.logging import Logger
from outception.models.email_log import EmailLogStatus
from outception.observability.task_logging import LoggableField
from outception.worker import AsyncSessionMaker, CronTrigger, TaskPriority, actor

from .react import render_from_json
from .repository import EmailLogRepository
from .sender import Attachment, email_sender

log: Logger = structlog.get_logger()


def _build_tags(template: str | None, email_props: dict[str, Any]) -> dict[str, str]:
    tags: dict[str, str] = {}
    if template is not None:
        tags["category"] = template
    return tags


@actor(actor_name="email.send", priority=TaskPriority.HIGH)
async def email_send(
    to_email_addr: str,
    subject: str,
    html_content: str | None,
    from_name: str,
    from_email_addr: str,
    email_headers: dict[str, str] | None,
    reply_to_name: str | None,
    reply_to_email_addr: str | None,
    template: Annotated[str | None, LoggableField] = None,
    props_json: str | None = None,
    attachments: list[Attachment] | None = None,
    deduplication_key: str | None = None,
) -> None:
    if html_content is None:
        assert template is not None
        assert props_json is not None
        html_content = await render_from_json(template, props_json)

    email_props = json.loads(props_json) if props_json else {}
    tags = _build_tags(template, email_props)

    processor_id: str | None = None
    status = EmailLogStatus.sent
    error: str | None = None

    try:
        processor_id = await email_sender.send(
            to_email_addr=to_email_addr,
            subject=subject,
            html_content=html_content,
            from_name=from_name,
            from_email_addr=from_email_addr,
            email_headers=email_headers,
            reply_to_name=reply_to_name,
            reply_to_email_addr=reply_to_email_addr,
            attachments=attachments,
            tags=tags,
        )
    except Exception as e:
        status = EmailLogStatus.failed
        error = str(e)
        raise
    finally:
        try:
            async with AsyncSessionMaker() as session:
                repository = EmailLogRepository.from_session(session)
                await repository.create_log(
                    status=status,
                    processor=settings.EMAIL_SENDER,
                    processor_id=processor_id,
                    to_email_addr=to_email_addr,
                    from_email_addr=from_email_addr,
                    from_name=from_name,
                    subject=subject,
                    email_template=template,
                    email_props=email_props,
                    error=error,
                    deduplication_key=deduplication_key,
                )
        except Exception:
            log.exception("Failed to write email log")


@actor(
    actor_name="email_log.prune",
    cron_trigger=CronTrigger(hour=0, minute=0),
    priority=TaskPriority.LOW,
    max_retries=0,
)
async def email_log_prune() -> None:
    async with AsyncSessionMaker() as session:
        repository = EmailLogRepository.from_session(session)
        await repository.delete_before(utc_now() - settings.EMAIL_LOG_RETENTION_PERIOD)
