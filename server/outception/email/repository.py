from datetime import datetime
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import delete

from outception.enums import EmailSender
from outception.kit.repository import RepositoryBase, RepositoryIDMixin
from outception.logging import Logger
from outception.models.email_log import (
    EmailLog,
    EmailLogStatus,
)

log: Logger = structlog.get_logger()


class EmailLogRepository(RepositoryBase[EmailLog], RepositoryIDMixin[EmailLog, UUID]):
    model = EmailLog

    async def get_by_processor_id(self, processor_id: str) -> EmailLog | None:
        statement = self.get_base_statement().where(
            EmailLog.processor_id == processor_id
        )
        return await self.get_one_or_none(statement)

    async def delete_before(self, before: datetime) -> None:
        statement = delete(EmailLog).where(EmailLog.created_at < before)
        await self.session.execute(statement)

    async def mark_failed(self, email_log: EmailLog, error: str) -> EmailLog:
        return await self.update(
            email_log,
            update_dict={
                "status": EmailLogStatus.failed,
                "error": error,
            },
        )

    async def create_log(
        self,
        *,
        status: EmailLogStatus,
        processor: EmailSender,
        to_email_addr: str,
        from_email_addr: str,
        from_name: str,
        subject: str,
        email_template: str | None = None,
        email_props: dict[str, Any] | None = None,
        processor_id: str | None = None,
        error: str | None = None,
        deduplication_key: str | None = None,
    ) -> EmailLog:
        props = email_props or {}
        return await self.create(
            EmailLog(
                status=status,
                processor=processor,
                to_email_addr=to_email_addr,
                from_email_addr=from_email_addr,
                from_name=from_name,
                subject=subject,
                email_template=email_template,
                email_props=props,
                processor_id=processor_id,
                error=error,
                deduplication_key=deduplication_key,
            )
        )
