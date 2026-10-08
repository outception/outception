import pytest
from httpx import AsyncClient
from pytest_mock import MockerFixture
from sqlalchemy import select

from outception.config import settings
from outception.feedback import service
from outception.models import Feedback
from outception.postgres import AsyncSession


@pytest.mark.asyncio
class TestFeedbackRoute:
    async def test_message_is_stored_scrubbed_without_an_account(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        response = await client.post(
            "/v1/feedback",
            json={
                "message": "The weather strip is wrong, mail me at a@b.io",
                "surface": "app",
                "context": {"page": "wall", "card": "bbc-world"},
            },
        )
        assert response.status_code == 204, response.text
        row = await session.scalar(select(Feedback))
        assert row is not None
        assert row.message == "The weather strip is wrong, mail me at [email]"
        assert row.surface == "app"
        assert row.context == {"page": "wall", "card": "bbc-world"}
        assert row.email is None
        assert row.sender_hash is not None
        assert not row.digested

    async def test_too_short_is_rejected(self, client: AsyncClient) -> None:
        response = await client.post("/v1/feedback", json={"message": "hi"})
        assert response.status_code == 422


@pytest.mark.asyncio
class TestDigest:
    async def test_digest_carries_undigested_messages_once(
        self, session: AsyncSession, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "FEEDBACK_DIGEST_EMAIL", "founder@example.com")
        enqueue = mocker.patch("outception.feedback.service.enqueue_job")
        session.add_all(
            [
                Feedback(message="first", surface="web"),
                Feedback(message="second", surface="app", email="r@example.com"),
            ]
        )
        await session.flush()
        assert await service.send_digest(session) == 2
        enqueue.assert_called_once()
        kwargs = enqueue.call_args.kwargs
        assert kwargs["to_email_addr"] == "founder@example.com"
        assert "2 message(s)" in kwargs["subject"]
        assert "first" in kwargs["html_content"]
        assert "r@example.com" in kwargs["html_content"]
        # Nothing new: nothing sent.
        assert await service.send_digest(session) == 0
        assert enqueue.call_count == 1

    async def test_no_address_sends_nothing(
        self, session: AsyncSession, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "FEEDBACK_DIGEST_EMAIL", None)
        enqueue = mocker.patch("outception.feedback.service.enqueue_job")
        session.add(Feedback(message="lonely", surface="web"))
        await session.flush()
        assert await service.send_digest(session) == 0
        enqueue.assert_not_called()
