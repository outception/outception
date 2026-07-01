from typing import Any

import pytest
from pytest_mock import MockerFixture

from outception.models import User
from outception.postgres import AsyncSession
from outception.promotion.service import promotion as promotion_service
from outception.promotion.tasks import promotion_send_lifecycle_email


class _FakeSessionMaker:
    """Make the actor's ``async with AsyncSessionMaker()`` reuse the test
    session (so it sees fixture-created rows) without closing it."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def __aenter__(self) -> AsyncSession:
        return self._session

    async def __aexit__(self, *args: Any) -> bool:
        return False


async def _make_pending(session: AsyncSession, user: User) -> Any:
    return await promotion_service.create_pending(
        session,
        author_id=user.id,
        category="tech",
        title="Hello",
        body="World",
        link="https://example.com",
        image_url=None,
        blocks=1,
    )


@pytest.mark.asyncio
class TestSendLifecycleEmail:
    async def test_enqueues_email_to_author(
        self, session: AsyncSession, user: User, mocker: MockerFixture
    ) -> None:
        promotion = await _make_pending(session, user)
        mocker.patch(
            "outception.promotion.tasks.AsyncSessionMaker",
            return_value=_FakeSessionMaker(session),
        )
        enqueue = mocker.patch("outception.promotion.tasks.enqueue_job")

        await promotion_send_lifecycle_email(str(promotion.id), "activated")

        enqueue.assert_called_once()
        assert enqueue.call_args.args[0] == "email.send"
        kwargs = enqueue.call_args.kwargs
        assert kwargs["to_email_addr"] == user.email
        assert "is live" in kwargs["subject"]
        assert kwargs["html_content"]
        assert kwargs["template"] is None

    async def test_skips_when_author_opted_out(
        self, session: AsyncSession, user: User, mocker: MockerFixture
    ) -> None:
        user.promotion_emails_enabled = False
        await session.flush()
        promotion = await _make_pending(session, user)
        mocker.patch(
            "outception.promotion.tasks.AsyncSessionMaker",
            return_value=_FakeSessionMaker(session),
        )
        enqueue = mocker.patch("outception.promotion.tasks.enqueue_job")

        await promotion_send_lifecycle_email(str(promotion.id), "activated")
        enqueue.assert_not_called()

    async def test_queued_email_includes_position(
        self, session: AsyncSession, user: User, mocker: MockerFixture
    ) -> None:
        first = await _make_pending(session, user)
        await promotion_service.activate_paid(
            session, first.id, external_ref="task:active"
        )  # occupies the slot
        second = await _make_pending(session, user)
        await promotion_service.activate_paid(
            session, second.id, external_ref="task:queued"
        )  # queued behind first

        mocker.patch(
            "outception.promotion.tasks.AsyncSessionMaker",
            return_value=_FakeSessionMaker(session),
        )
        enqueue = mocker.patch("outception.promotion.tasks.enqueue_job")

        await promotion_send_lifecycle_email(str(second.id), "queued")

        enqueue.assert_called_once()
        html = enqueue.call_args.kwargs["html_content"]
        assert "in line" in html
        assert "#1" in html  # first (and only) queued promotion

    async def test_missing_promotion_is_noop(
        self, session: AsyncSession, mocker: MockerFixture
    ) -> None:
        from uuid import uuid4

        mocker.patch(
            "outception.promotion.tasks.AsyncSessionMaker",
            return_value=_FakeSessionMaker(session),
        )
        enqueue = mocker.patch("outception.promotion.tasks.enqueue_job")

        await promotion_send_lifecycle_email(str(uuid4()), "activated")
        enqueue.assert_not_called()
