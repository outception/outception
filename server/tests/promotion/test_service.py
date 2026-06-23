from unittest.mock import AsyncMock

import httpx
import pytest
from pytest_mock import MockerFixture

from polar.config import settings
from polar.models import User
from polar.models.promotion import Promotion, PromotionStatus
from polar.postgres import AsyncSession
from polar.promotion.repository import PromotionRepository
from polar.promotion.service import promotion as promotion_service


async def _make_pending(
    session: AsyncSession, user: User, *, blocks: int = 2
) -> Promotion:
    return await promotion_service.create_pending(
        session,
        author_id=user.id,
        category="tech",
        title="Hello",
        body="World",
        link="https://example.com",
        image_url=None,
        blocks=blocks,
    )


@pytest.mark.asyncio
class TestCreatePending:
    async def test_freezes_price_and_duration(
        self, session: AsyncSession, user: User
    ) -> None:
        promotion = await _make_pending(session, user, blocks=3)
        assert promotion.status == PromotionStatus.PENDING_PAYMENT
        assert promotion.duration_minutes == 3 * 10
        assert promotion.amount_cents == 3 * 1000


@pytest.mark.asyncio
class TestActivatePaid:
    async def test_activates_and_advances(
        self, session: AsyncSession, user: User
    ) -> None:
        promotion = await _make_pending(session, user)
        await promotion_service.activate_paid(
            session, promotion.id, external_ref="order:abc"
        )
        repo = PromotionRepository.from_session(session)
        refreshed = await repo.get_by_id(promotion.id)
        assert refreshed is not None
        # Empty category → promoted straight to ACTIVE.
        assert refreshed.status == PromotionStatus.ACTIVE
        assert refreshed.payment_ref == "order:abc"
        assert refreshed.active_until is not None

    async def test_idempotent_on_external_ref(
        self, session: AsyncSession, user: User
    ) -> None:
        first = await _make_pending(session, user)
        second = await _make_pending(session, user)
        await promotion_service.activate_paid(
            session, first.id, external_ref="order:dup"
        )
        # Same order ref must not pay a second promotion.
        await promotion_service.activate_paid(
            session, second.id, external_ref="order:dup"
        )
        repo = PromotionRepository.from_session(session)
        second_refreshed = await repo.get_by_id(second.id)
        assert second_refreshed is not None
        assert second_refreshed.status == PromotionStatus.PENDING_PAYMENT

    async def test_second_paid_promotion_queues(
        self, session: AsyncSession, user: User
    ) -> None:
        first = await _make_pending(session, user)
        second = await _make_pending(session, user)
        await promotion_service.activate_paid(
            session, first.id, external_ref="order:1"
        )
        await promotion_service.activate_paid(
            session, second.id, external_ref="order:2"
        )
        repo = PromotionRepository.from_session(session)
        refreshed = await repo.get_by_id(second.id)
        assert refreshed is not None
        assert refreshed.status == PromotionStatus.QUEUED


@pytest.mark.asyncio
class TestEngagementCounters:
    async def test_get_featured_increments_impressions(
        self, session: AsyncSession, user: User
    ) -> None:
        promotion = await _make_pending(session, user)
        await promotion_service.activate_paid(
            session, promotion.id, external_ref="order:imp"
        )
        featured = await promotion_service.get_featured(session, ["tech"])
        assert [p.id for p in featured] == [promotion.id]
        repo = PromotionRepository.from_session(session)
        refreshed = await repo.get_by_id(promotion.id)
        assert refreshed is not None
        assert refreshed.impressions == 1

    async def test_track_click_increments_and_returns_link(
        self, session: AsyncSession, user: User
    ) -> None:
        promotion = await _make_pending(session, user)
        link = await promotion_service.track_click(session, promotion.id)
        assert link == "https://example.com"
        repo = PromotionRepository.from_session(session)
        refreshed = await repo.get_by_id(promotion.id)
        assert refreshed is not None
        assert refreshed.clicks == 1


@pytest.mark.asyncio
class TestTinybirdEmission:
    def _enqueued_event_names(self, enqueue_mock: object) -> list[str]:
        names: list[str] = []
        for call in enqueue_mock.call_args_list:  # type: ignore[attr-defined]
            assert call.args[0] == "promotion.emit_events"
            names.extend(event["name"] for event in call.kwargs["events"])
        return names

    async def test_lifecycle_emits_events(
        self, mocker: MockerFixture, session: AsyncSession, user: User
    ) -> None:
        enqueue_mock = mocker.patch("polar.promotion.events.enqueue_job")

        promotion = await _make_pending(session, user)
        await promotion_service.activate_paid(
            session, promotion.id, external_ref="order:tb"
        )
        await promotion_service.get_featured(session, ["tech"])
        await promotion_service.track_click(session, promotion.id)

        names = self._enqueued_event_names(enqueue_mock)
        assert "promotion_created" in names
        assert "promotion_paid" in names
        assert "promotion_activated" in names
        assert "promotion_impression" in names
        assert "promotion_click" in names

    async def test_no_events_when_no_active_promotions(
        self, mocker: MockerFixture, session: AsyncSession
    ) -> None:
        enqueue_mock = mocker.patch("polar.promotion.events.enqueue_job")
        await promotion_service.get_featured(session, ["tech"])
        enqueue_mock.assert_not_called()


@pytest.mark.asyncio
class TestTinybirdAnalyticsRead:
    async def test_returns_none_when_unconfigured(
        self, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "is_tinybird_configured", return_value=False)
        result = await promotion_service.analytics_timeseries_tinybird(
            author_id=None, days=30
        )
        assert result is None

    async def test_returns_rows_when_configured(
        self, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "is_tinybird_configured", return_value=True)
        rows = [
            {
                "timestamp": "2026-06-01T00:00:00",
                "spend_cents": 1000,
                "impressions": 5,
                "clicks": 2,
                "promotions": 1,
            }
        ]
        query_mock = mocker.patch(
            "polar.promotion.service.tinybird_client.query_pipe",
            new=AsyncMock(return_value=rows),
        )
        result = await promotion_service.analytics_timeseries_tinybird(
            author_id=None, days=7
        )
        assert result == rows
        query_mock.assert_awaited_once()
        await_args = query_mock.await_args
        assert await_args is not None
        assert await_args.args[0] == "promotion_analytics"
        assert await_args.args[1]["days"] == 7

    async def test_returns_none_on_query_error(
        self, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "is_tinybird_configured", return_value=True)
        mocker.patch(
            "polar.promotion.service.tinybird_client.query_pipe",
            new=AsyncMock(side_effect=httpx.HTTPError("boom")),
        )
        result = await promotion_service.analytics_timeseries_tinybird(
            author_id=None, days=30
        )
        assert result is None


@pytest.mark.asyncio
class TestLifecycleNotifications:
    @staticmethod
    def _kinds_for(enqueue_mock: AsyncMock, promotion_id: object) -> list[str]:
        return [
            call.kwargs["kind"]
            for call in enqueue_mock.call_args_list
            if call.args[0] == "promotion.send_lifecycle_email"
            and call.kwargs["promotion_id"] == str(promotion_id)
        ]

    async def test_activation_notifies_author(
        self, mocker: MockerFixture, session: AsyncSession, user: User
    ) -> None:
        enqueue_mock = mocker.patch("polar.promotion.notifications.enqueue_job")
        promotion = await _make_pending(session, user)
        await promotion_service.activate_paid(
            session, promotion.id, external_ref="order:notify"
        )
        assert "activated" in self._kinds_for(enqueue_mock, promotion.id)

    async def test_expiry_notifies_author(
        self, mocker: MockerFixture, session: AsyncSession, user: User
    ) -> None:
        from datetime import timedelta

        from polar.kit.utils import utc_now

        promotion = await _make_pending(session, user)
        await promotion_service.activate_paid(
            session, promotion.id, external_ref="order:expire"
        )
        repo = PromotionRepository.from_session(session)
        active = await repo.get_by_id(promotion.id)
        assert active is not None
        active.active_until = utc_now() - timedelta(minutes=1)
        await session.flush()

        # Mock only now so we capture the expiry notification, not activation.
        enqueue_mock = mocker.patch("polar.promotion.notifications.enqueue_job")
        await promotion_service.get_featured(session, ["tech"])
        assert "expired" in self._kinds_for(enqueue_mock, promotion.id)
