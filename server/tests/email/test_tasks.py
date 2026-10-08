import contextlib
from collections.abc import AsyncIterator
from datetime import timedelta

import pytest
from pytest_mock import MockerFixture
from sqlalchemy import select

from outception.config import settings
from outception.email.repository import EmailLogRepository
from outception.email.sender import SendEmailError
from outception.email.tasks import email_log_prune, email_send
from outception.enums import EmailSender
from outception.kit.utils import utc_now
from outception.models.email_log import EmailLog, EmailLogStatus
from outception.postgres import AsyncSession
from tests.fixtures.database import SaveFixture
from tests.fixtures.random_objects import create_email_log


@contextlib.asynccontextmanager
async def _session_maker(session: AsyncSession) -> AsyncIterator[AsyncSession]:
    yield session


@pytest.mark.asyncio
class TestEmailSend:
    async def test_successful_send(
        self,
        session: AsyncSession,
        mocker: MockerFixture,
    ) -> None:
        mock_send = mocker.patch(
            "outception.email.tasks.email_sender.send",
            return_value="message_123",
        )

        await email_send(
            to_email_addr="test@example.com",
            subject="Test Subject",
            html_content="<p>Hello</p>",
            from_name="Outception",
            from_email_addr="noreply@outception.sh",
            email_headers=None,
            reply_to_name=None,
            reply_to_email_addr=None,
        )

        mock_send.assert_called_once()

        result = await session.execute(select(EmailLog))
        log = result.scalar_one()
        assert log.status == EmailLogStatus.sent
        assert log.processor_id == "message_123"
        assert log.to_email_addr == "test@example.com"
        assert log.subject == "Test Subject"
        assert log.error is None

    async def test_failed_send_creates_log_and_reraises(
        self,
        session: AsyncSession,
        mocker: MockerFixture,
    ) -> None:
        mocker.patch(
            "outception.email.tasks.email_sender.send",
            side_effect=SendEmailError("connection refused"),
        )

        with pytest.raises(SendEmailError):
            await email_send(
                to_email_addr="test@example.com",
                subject="Test Subject",
                html_content="<p>Hello</p>",
                from_name="Outception",
                from_email_addr="noreply@outception.sh",
                email_headers=None,
                reply_to_name=None,
                reply_to_email_addr=None,
            )

        result = await session.execute(select(EmailLog))
        log = result.scalar_one()
        assert log.status == EmailLogStatus.failed
        assert log.processor_id is None
        assert log.error == "connection refused"

    async def test_persists_deduplication_key(
        self,
        session: AsyncSession,
        mocker: MockerFixture,
    ) -> None:
        mocker.patch(
            "outception.email.tasks.email_sender.send",
            return_value="message_123",
        )

        await email_send(
            to_email_addr="test@example.com",
            subject="Test Subject",
            html_content="<p>Hello</p>",
            from_name="Outception",
            from_email_addr="noreply@outception.sh",
            email_headers=None,
            reply_to_name=None,
            reply_to_email_addr=None,
            deduplication_key="some_reminder:abc:2026-4",
        )

        result = await session.execute(select(EmailLog))
        log = result.scalar_one()
        assert log.deduplication_key == "some_reminder:abc:2026-4"

    async def test_processor_reflects_settings(
        self,
        session: AsyncSession,
        mocker: MockerFixture,
    ) -> None:
        mocker.patch(
            "outception.email.tasks.email_sender.send",
            return_value=None,
        )
        mocker.patch(
            "outception.email.tasks.settings.EMAIL_SENDER",
            EmailSender.logger,
        )

        await email_send(
            to_email_addr="test@example.com",
            subject="Test",
            html_content="<p>Hi</p>",
            from_name="Outception",
            from_email_addr="noreply@outception.sh",
            email_headers=None,
            reply_to_name=None,
            reply_to_email_addr=None,
        )

        result = await session.execute(select(EmailLog))
        log = result.scalar_one()
        assert log.processor == EmailSender.logger

    async def test_log_failure_does_not_mask_send_error(
        self,
        session: AsyncSession,
        mocker: MockerFixture,
    ) -> None:
        mocker.patch(
            "outception.email.tasks.email_sender.send",
            side_effect=SendEmailError("send failed"),
        )
        mocker.patch(
            "outception.email.tasks.AsyncSessionMaker",
            side_effect=RuntimeError("db down"),
        )
        log_exception = mocker.patch("outception.email.tasks.log.exception")

        with pytest.raises(SendEmailError, match="send failed"):
            await email_send(
                to_email_addr="test@example.com",
                subject="Test",
                html_content="<p>Hi</p>",
                from_name="Outception",
                from_email_addr="noreply@outception.sh",
                email_headers=None,
                reply_to_name=None,
                reply_to_email_addr=None,
            )

        log_exception.assert_called_once_with("Failed to write email log")


@pytest.mark.asyncio
class TestEmailLogPrune:
    async def test_deletes_logs_past_retention_period(
        self,
        session: AsyncSession,
        save_fixture: SaveFixture,
        mocker: MockerFixture,
    ) -> None:
        mocker.patch(
            "outception.email.tasks.AsyncSessionMaker",
            side_effect=lambda: _session_maker(session),
        )
        retention = settings.EMAIL_LOG_RETENTION_PERIOD
        expired = await create_email_log(
            save_fixture, created_at=utc_now() - retention - timedelta(days=1)
        )
        retained = await create_email_log(
            save_fixture, created_at=utc_now() - retention + timedelta(days=1)
        )

        await email_log_prune()

        repository = EmailLogRepository.from_session(session)
        assert await repository.get_by_id(expired.id) is None
        assert await repository.get_by_id(retained.id) is not None
