import json

import structlog

from outception.config import settings
from outception.logging import Logger
from outception.models.email_log import EmailLogStatus
from outception.worker import AsyncSessionMaker, TaskPriority, actor

from .react import render_from_json
from .repository import EmailLogRepository
from .sender import Attachment, email_sender

log: Logger = structlog.get_logger()

# Prop keys whose values are live credentials (login OTP, leaked-token notices,
# the verification link that carries a raw token). email_logs is a long-lived,
# un-swept audit table, so these must never be persisted in cleartext.
_SENSITIVE_PROP_KEYS = frozenset(
    {"code", "token", "url", "personal_access_token", "organization_access_token"}
)
_REDACTED = "[REDACTED]"


def _redact_props(props: dict[str, object]) -> tuple[dict[str, object], list[str]]:
    """Return a copy of ``props`` with sensitive values masked, plus the list of
    raw secret values removed (so they can also be scrubbed from an error blob)."""
    redacted: dict[str, object] = {}
    secrets: list[str] = []
    for key, value in props.items():
        if key in _SENSITIVE_PROP_KEYS and value:
            if isinstance(value, str):
                secrets.append(value)
            redacted[key] = _REDACTED
        else:
            redacted[key] = value
    return redacted, secrets


def _scrub_error(error: str | None, secrets: list[str]) -> str | None:
    """Remove any raw secret value that leaked into a renderer/sender error."""
    if not error:
        return error
    for secret in secrets:
        if secret:
            error = error.replace(secret, _REDACTED)
    return error


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
    template: str | None = None,
    props_json: str | None = None,
    attachments: list[Attachment] | None = None,
) -> None:
    if html_content is None:
        assert template is not None
        assert props_json is not None
        html_content = render_from_json(template, props_json)

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
        )
    except Exception as e:
        status = EmailLogStatus.failed
        error = str(e)
        raise
    finally:
        try:
            raw_props = json.loads(props_json) if props_json else {}
            email_props, secrets = _redact_props(raw_props)

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
                    error=_scrub_error(error, secrets),
                )
        except Exception:
            log.exception("Failed to write email log")
