from abc import ABC, abstractmethod
from collections.abc import Iterable
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from typing import TYPE_CHECKING, Any, TypedDict

import aiosmtplib
import httpx
import structlog
from email_validator import validate_email

from outception.config import settings
from outception.enums import EmailSender as EmailSenderType
from outception.exceptions import OutceptionError
from outception.logging import Logger
from outception.worker import enqueue_job

from .react import serialize_email_props

if TYPE_CHECKING:
    from .schemas import Email

log: Logger = structlog.get_logger()

DEFAULT_FROM_NAME = settings.EMAIL_FROM_NAME
DEFAULT_FROM_EMAIL_ADDRESS = f"{settings.EMAIL_FROM_LOCAL}@{settings.EMAIL_FROM_DOMAIN}"
DEFAULT_REPLY_TO_NAME = settings.EMAIL_DEFAULT_REPLY_TO_NAME
DEFAULT_REPLY_TO_EMAIL_ADDRESS = settings.EMAIL_DEFAULT_REPLY_TO_EMAIL_ADDRESS


def to_ascii_email(email: str) -> str:
    """
    Convert an email address to ASCII format, possibly using punycode for internationalized domains.
    """
    validated_email = validate_email(email, check_deliverability=False)
    return validated_email.ascii_email or email


class EmailSenderError(OutceptionError): ...


class EmailSenderOperationalError(EmailSenderError):
    """Operational error for email sender (e.g., timeout, network issues)."""

    pass


class SendEmailError(EmailSenderError):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class Attachment(TypedDict):
    remote_url: str
    filename: str


class EmailSender(ABC):
    @abstractmethod
    async def send(
        self,
        *,
        to_email_addr: str,
        subject: str,
        html_content: str,
        from_name: str = DEFAULT_FROM_NAME,
        from_email_addr: str = DEFAULT_FROM_EMAIL_ADDRESS,
        email_headers: dict[str, str] | None = None,
        reply_to_name: str | None = DEFAULT_REPLY_TO_NAME,
        reply_to_email_addr: str | None = DEFAULT_REPLY_TO_EMAIL_ADDRESS,
        attachments: Iterable[Attachment] | None = None,
    ) -> str | None:
        pass


class LoggingEmailSender(EmailSender):
    async def send(
        self,
        *,
        to_email_addr: str,
        subject: str,
        html_content: str,
        from_name: str = DEFAULT_FROM_NAME,
        from_email_addr: str = DEFAULT_FROM_EMAIL_ADDRESS,
        email_headers: dict[str, str] | None = None,
        reply_to_name: str | None = DEFAULT_REPLY_TO_NAME,
        reply_to_email_addr: str | None = DEFAULT_REPLY_TO_EMAIL_ADDRESS,
        attachments: Iterable[Attachment] | None = None,
    ) -> str | None:
        log.info(
            "Sending an email",
            to_email_addr=to_ascii_email(to_email_addr),
            subject=subject,
            from_name=from_name,
            from_email_addr=to_ascii_email(from_email_addr),
        )
        return None


class ResendEmailSender(EmailSender):
    def __init__(self) -> None:
        self.client = httpx.AsyncClient(
            base_url=settings.RESEND_API_BASE_URL,
            headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
        )

    async def send(
        self,
        *,
        to_email_addr: str,
        subject: str,
        html_content: str,
        from_name: str = DEFAULT_FROM_NAME,
        from_email_addr: str = DEFAULT_FROM_EMAIL_ADDRESS,
        email_headers: dict[str, str] | None = None,
        reply_to_name: str | None = DEFAULT_REPLY_TO_NAME,
        reply_to_email_addr: str | None = DEFAULT_REPLY_TO_EMAIL_ADDRESS,
        attachments: Iterable[Attachment] | None = None,
    ) -> str | None:
        to_email_addr_ascii = to_ascii_email(to_email_addr)
        payload: dict[str, Any] = {
            "from": f"{from_name} <{to_ascii_email(from_email_addr)}>",
            "to": [to_email_addr_ascii],
            "subject": subject,
            "html": html_content,
            "headers": email_headers or {},
            "attachments": [
                {
                    "path": attachment["remote_url"],
                    "filename": attachment["filename"],
                }
                for attachment in attachments
            ]
            if attachments
            else [],
        }
        if reply_to_name and reply_to_email_addr:
            payload["reply_to"] = (
                f"{reply_to_name} <{to_ascii_email(reply_to_email_addr)}>"
            )

        try:
            response = await self.client.post("/emails", json=payload)
            response.raise_for_status()
            email = response.json()
        except httpx.RequestError as e:
            log.warning(
                "resend.send_network_error",
                to_email_addr=to_email_addr_ascii,
                subject=subject,
                error=e,
            )
            raise EmailSenderOperationalError(str(e)) from e
        except httpx.HTTPError as e:
            log.warning(
                "resend.send_error",
                to_email_addr=to_email_addr_ascii,
                subject=subject,
                error=e,
            )
            raise SendEmailError(str(e)) from e

        log.info(
            "resend.send",
            to_email_addr=to_email_addr_ascii,
            subject=subject,
            email_id=email["id"],
        )

        return email["id"]


class SmtpEmailSender(EmailSender):
    """Send via SMTP (e.g. Gmail / Google Workspace). Configured through the
    EMAIL_SMTP_* settings. Note Gmail's ~2,000/day sending cap — over it, sends
    are rejected until the window resets (no billing; just deferred delivery)."""

    async def send(
        self,
        *,
        to_email_addr: str,
        subject: str,
        html_content: str,
        from_name: str = DEFAULT_FROM_NAME,
        from_email_addr: str = DEFAULT_FROM_EMAIL_ADDRESS,
        email_headers: dict[str, str] | None = None,
        reply_to_name: str | None = DEFAULT_REPLY_TO_NAME,
        reply_to_email_addr: str | None = DEFAULT_REPLY_TO_EMAIL_ADDRESS,
        attachments: Iterable[Attachment] | None = None,
    ) -> str | None:
        to_ascii = to_ascii_email(to_email_addr)
        from_ascii = to_ascii_email(from_email_addr)

        message = EmailMessage()
        message["From"] = formataddr((from_name, from_ascii))
        message["To"] = to_ascii
        message["Subject"] = subject
        message_id = make_msgid(domain=from_ascii.rsplit("@", 1)[-1])
        message["Message-ID"] = message_id
        if reply_to_name and reply_to_email_addr:
            message["Reply-To"] = formataddr(
                (reply_to_name, to_ascii_email(reply_to_email_addr))
            )
        for key, value in (email_headers or {}).items():
            message[key] = value
        message.set_content("This message requires an HTML-capable email client.")
        message.add_alternative(html_content, subtype="html")

        if attachments:
            async with httpx.AsyncClient() as client:
                for attachment in attachments:
                    try:
                        resp = await client.get(attachment["remote_url"], timeout=15)
                        resp.raise_for_status()
                    except httpx.HTTPError as e:
                        raise EmailSenderOperationalError(
                            f"attachment fetch failed: {e}"
                        ) from e
                    ctype = resp.headers.get("content-type", "application/octet-stream")
                    maintype, _, subtype = ctype.partition("/")
                    message.add_attachment(
                        resp.content,
                        maintype=maintype or "application",
                        subtype=subtype or "octet-stream",
                        filename=attachment["filename"],
                    )

        implicit_tls = settings.EMAIL_SMTP_PORT == 465
        try:
            await aiosmtplib.send(
                message,
                hostname=settings.EMAIL_SMTP_HOST,
                port=settings.EMAIL_SMTP_PORT,
                username=settings.EMAIL_SMTP_USER or None,
                password=settings.EMAIL_SMTP_PASSWORD or None,
                start_tls=settings.EMAIL_SMTP_STARTTLS and not implicit_tls,
                use_tls=implicit_tls,
                timeout=30,
            )
        except (
            aiosmtplib.SMTPConnectError,
            aiosmtplib.SMTPTimeoutError,
            aiosmtplib.SMTPServerDisconnected,
        ) as e:
            log.warning(
                "smtp.send_network_error",
                to_email_addr=to_ascii,
                subject=subject,
                error=str(e),
            )
            raise EmailSenderOperationalError(str(e)) from e
        except aiosmtplib.SMTPException as e:
            log.warning(
                "smtp.send_error",
                to_email_addr=to_ascii,
                subject=subject,
                error=str(e),
            )
            raise SendEmailError(str(e)) from e

        log.info(
            "smtp.send", to_email_addr=to_ascii, subject=subject, message_id=message_id
        )
        return message_id


def enqueue_email_template(
    email: "Email",
    *,
    to_email_addr: str,
    subject: str,
    from_name: str = DEFAULT_FROM_NAME,
    from_email_addr: str = DEFAULT_FROM_EMAIL_ADDRESS,
    email_headers: dict[str, str] | None = None,
    reply_to_name: str | None = DEFAULT_REPLY_TO_NAME,
    reply_to_email_addr: str | None = DEFAULT_REPLY_TO_EMAIL_ADDRESS,
    attachments: Iterable[Attachment] | None = None,
) -> None:
    enqueue_job(
        "email.send",
        to_email_addr=to_email_addr,
        subject=subject,
        html_content=None,
        template=email.template,
        props_json=serialize_email_props(email),
        from_name=from_name,
        from_email_addr=from_email_addr,
        email_headers=email_headers,
        reply_to_name=reply_to_name,
        reply_to_email_addr=reply_to_email_addr,
        attachments=attachments,
    )


email_sender: EmailSender
if settings.EMAIL_SENDER == EmailSenderType.resend:
    email_sender = ResendEmailSender()
elif settings.EMAIL_SENDER == EmailSenderType.smtp:
    email_sender = SmtpEmailSender()
else:
    # Logging in development
    email_sender = LoggingEmailSender()
