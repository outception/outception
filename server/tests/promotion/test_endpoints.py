from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from pytest_mock import MockerFixture

from polar.auth.scope import Scope
from polar.config import settings
from polar.models import User
from polar.models.promotion import Promotion, PromotionStatus
from polar.postgres import AsyncSession
from polar.promotion.repository import PromotionRepository
from polar.promotion.service import PRICE_CENTS_PER_BLOCK
from polar.promotion.service import promotion as promotion_service
from tests.fixtures.auth import AuthSubjectFixture


async def _make_pending(
    session: AsyncSession, user: User, *, category: str = "tech", blocks: int = 2
) -> Promotion:
    return await promotion_service.create_pending(
        session,
        author_id=user.id,
        category=category,
        title="Hello",
        body="World",
        link="https://example.com",
        image_url=None,
        blocks=blocks,
    )


@pytest.mark.asyncio
class TestGetPricing:
    async def test_public(self, client: AsyncClient) -> None:
        response = await client.get("/v1/promotions/pricing")
        assert response.status_code == 200
        body = response.json()
        assert body["block_minutes"] > 0
        assert body["price_cents"] > 0


@pytest.mark.asyncio
class TestCreatePromotion:
    async def test_anonymous(self, client: AsyncClient) -> None:
        response = await client.post(
            "/v1/promotions/",
            json={"category": "tech", "title": "Hi", "body": "There", "blocks": 1},
        )
        assert response.status_code == 401

    @pytest.mark.auth
    async def test_unconfigured_returns_503(
        self, client: AsyncClient, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "PROMOTION_PRODUCT_ID", "")
        response = await client.post(
            "/v1/promotions/",
            json={"category": "tech", "title": "Hi", "body": "There", "blocks": 1},
        )
        assert response.status_code == 503

    @pytest.mark.auth
    async def test_creates_draft_and_returns_checkout_url(
        self,
        client: AsyncClient,
        session: AsyncSession,
        user: User,
        mocker: MockerFixture,
    ) -> None:
        mocker.patch.object(settings, "PROMOTION_PRODUCT_ID", "prod_123")
        checkout_mock = mocker.patch(
            "polar.billing.service.payment_gateway_client.create_checkout",
            new=AsyncMock(return_value="https://checkout.example/abc"),
        )

        response = await client.post(
            "/v1/promotions/",
            json={
                "category": "tech",
                "title": "Buy me",
                "body": "Great deal",
                "link": "https://example.com",
                "blocks": 3,
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["url"] == "https://checkout.example/abc"

        repo = PromotionRepository.from_session(session)
        promotion = await repo.get_by_id(body["promotion_id"])
        assert promotion is not None
        assert promotion.status == PromotionStatus.PENDING_PAYMENT
        assert promotion.author_id == user.id
        assert promotion.amount_cents == 3 * PRICE_CENTS_PER_BLOCK

        checkout_mock.assert_awaited_once()
        assert checkout_mock.await_args is not None
        kwargs = checkout_mock.await_args.kwargs
        assert kwargs["amount"] == promotion.amount_cents
        assert kwargs["metadata"]["promotion_id"] == str(promotion.id)

    @pytest.mark.auth
    @pytest.mark.parametrize("field", ["link", "image_url"])
    @pytest.mark.parametrize(
        "value", ["javascript:alert(1)", "data:text/html,x", "not a url", "ftp://x"]
    )
    async def test_rejects_non_http_url(
        self, client: AsyncClient, mocker: MockerFixture, field: str, value: str
    ) -> None:
        mocker.patch.object(settings, "PROMOTION_PRODUCT_ID", "prod_123")
        response = await client.post(
            "/v1/promotions/",
            json={
                "category": "tech",
                "title": "Buy me",
                "body": "Great deal",
                field: value,
                "blocks": 1,
            },
        )
        assert response.status_code == 422

    @pytest.mark.auth
    @pytest.mark.parametrize("category", ["", "bogus", "News", "tech ", "politics"])
    async def test_rejects_unknown_category(
        self, client: AsyncClient, mocker: MockerFixture, category: str
    ) -> None:
        mocker.patch.object(settings, "PROMOTION_PRODUCT_ID", "prod_123")
        response = await client.post(
            "/v1/promotions/",
            json={
                "category": category,
                "title": "Buy me",
                "body": "Great deal",
                "blocks": 1,
            },
        )
        assert response.status_code == 422

    @pytest.mark.auth
    async def test_accepts_http_image_url(
        self, client: AsyncClient, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "PROMOTION_PRODUCT_ID", "prod_123")
        mocker.patch(
            "polar.billing.service.payment_gateway_client.create_checkout",
            new=AsyncMock(return_value="https://checkout.example/abc"),
        )
        response = await client.post(
            "/v1/promotions/",
            json={
                "category": "tech",
                "title": "Buy me",
                "body": "Great deal",
                "image_url": "https://cdn.example.com/a.png",
                "blocks": 1,
            },
        )
        assert response.status_code == 200

    @pytest.mark.auth(AuthSubjectFixture(scopes={Scope.promotions_read}))
    async def test_read_scope_cannot_create(
        self, client: AsyncClient, mocker: MockerFixture
    ) -> None:
        # A token with only promotions:read must not be able to start a paid
        # checkout — buying requires promotions:write.
        mocker.patch.object(settings, "PROMOTION_PRODUCT_ID", "prod_123")
        response = await client.post(
            "/v1/promotions/",
            json={"category": "tech", "title": "Hi", "body": "There", "blocks": 1},
        )
        assert response.status_code == 403


@pytest.mark.asyncio
class TestPreferences:
    async def test_anonymous(self, client: AsyncClient) -> None:
        assert (await client.get("/v1/promotions/preferences")).status_code == 401

    @pytest.mark.auth
    async def test_get_defaults_to_enabled(self, client: AsyncClient) -> None:
        response = await client.get("/v1/promotions/preferences")
        assert response.status_code == 200
        assert response.json() == {"promotion_emails_enabled": True}

    @pytest.mark.auth
    async def test_patch_toggles_and_persists(
        self, client: AsyncClient, session: AsyncSession, user: User
    ) -> None:
        response = await client.patch(
            "/v1/promotions/preferences",
            json={"promotion_emails_enabled": False},
        )
        assert response.status_code == 200
        assert response.json() == {"promotion_emails_enabled": False}

        await session.refresh(user)
        assert user.promotion_emails_enabled is False


@pytest.mark.asyncio
class TestListMine:
    async def test_anonymous(self, client: AsyncClient) -> None:
        response = await client.get("/v1/promotions/mine")
        assert response.status_code == 401

    @pytest.mark.auth(AuthSubjectFixture(scopes={Scope.promotions_read}))
    async def test_read_scope_allows(self, client: AsyncClient) -> None:
        # promotions:read is enough to read your own promotions.
        response = await client.get("/v1/promotions/mine")
        assert response.status_code == 200

    @pytest.mark.auth(AuthSubjectFixture(scopes={Scope.user_read}))
    async def test_without_promotion_scope_forbidden(
        self, client: AsyncClient
    ) -> None:
        # A token carrying no promotion scope can't read promotions.
        response = await client.get("/v1/promotions/mine")
        assert response.status_code == 403

    @pytest.mark.auth
    async def test_lists_only_own(
        self,
        client: AsyncClient,
        session: AsyncSession,
        user: User,
        user_second: User,
    ) -> None:
        mine = await _make_pending(session, user)
        await _make_pending(session, user_second)

        response = await client.get("/v1/promotions/mine")
        assert response.status_code == 200
        body = response.json()
        ids = {row["id"] for row in body}
        assert str(mine.id) in ids
        assert all(row["author_id"] == str(user.id) for row in body)
        # owner view exposes per-promotion engagement counters
        row = next(r for r in body if r["id"] == str(mine.id))
        assert row["impressions"] == 0
        assert row["clicks"] == 0


@pytest.mark.asyncio
class TestGetFeatured:
    async def test_empty_categories(self, client: AsyncClient) -> None:
        response = await client.get(
            "/v1/promotions/featured", params={"categories": ""}
        )
        assert response.status_code == 200
        assert response.json() == []

    async def test_returns_active(
        self, client: AsyncClient, session: AsyncSession, user: User
    ) -> None:
        promotion = await _make_pending(session, user, category="news")
        await promotion_service.activate_paid(
            session, promotion.id, external_ref="order:feat"
        )

        response = await client.get(
            "/v1/promotions/featured", params={"categories": "news"}
        )
        assert response.status_code == 200
        body = response.json()
        assert any(row["id"] == str(promotion.id) for row in body)

    async def test_repeat_views_dedupe_impressions(
        self, client: AsyncClient, session: AsyncSession, user: User
    ) -> None:
        promotion = await _make_pending(session, user, category="news")
        await promotion_service.activate_paid(
            session, promotion.id, external_ref="order:feat_dedup"
        )

        # Same client (same IP + user-agent) polling the wall repeatedly.
        for _ in range(3):
            response = await client.get(
                "/v1/promotions/featured", params={"categories": "news"}
            )
            assert response.status_code == 200

        repo = PromotionRepository.from_session(session)
        refreshed = await repo.get_by_id(promotion.id)
        assert refreshed is not None
        assert refreshed.impressions == 1


@pytest.mark.asyncio
class TestClickPromotion:
    async def test_redirects_to_link_and_tracks(
        self, client: AsyncClient, session: AsyncSession, user: User
    ) -> None:
        promotion = await _make_pending(session, user)
        await promotion_service.activate_paid(
            session, promotion.id, external_ref="order:click"
        )

        response = await client.get(
            f"/v1/promotions/{promotion.id}/click", follow_redirects=False
        )
        assert response.status_code == 302
        assert response.headers["location"] == "https://example.com"

        repo = PromotionRepository.from_session(session)
        refreshed = await repo.get_by_id(promotion.id)
        assert refreshed is not None
        assert refreshed.clicks == 1

    async def test_repeat_clicks_dedupe_count(
        self, client: AsyncClient, session: AsyncSession, user: User
    ) -> None:
        promotion = await _make_pending(session, user)
        await promotion_service.activate_paid(
            session, promotion.id, external_ref="order:click_dedup"
        )

        # Same client clicking repeatedly always redirects, counts once.
        for _ in range(3):
            response = await client.get(
                f"/v1/promotions/{promotion.id}/click", follow_redirects=False
            )
            assert response.status_code == 302
            assert response.headers["location"] == "https://example.com"

        repo = PromotionRepository.from_session(session)
        refreshed = await repo.get_by_id(promotion.id)
        assert refreshed is not None
        assert refreshed.clicks == 1

    async def test_unknown_falls_back_to_frontend(self, client: AsyncClient) -> None:
        from uuid import uuid4

        response = await client.get(
            f"/v1/promotions/{uuid4()}/click", follow_redirects=False
        )
        assert response.status_code == 302
        assert response.headers["location"] == settings.FRONTEND_BASE_URL


@pytest.mark.asyncio
class TestGetAnalytics:
    async def test_anonymous(self, client: AsyncClient) -> None:
        response = await client.get("/v1/promotions/analytics")
        assert response.status_code == 401

    @pytest.mark.auth
    async def test_totals_from_postgres(
        self,
        client: AsyncClient,
        session: AsyncSession,
        user: User,
        mocker: MockerFixture,
    ) -> None:
        mocker.patch.object(settings, "is_tinybird_configured", return_value=False)
        promotion = await _make_pending(session, user)
        await promotion_service.activate_paid(
            session, promotion.id, external_ref="order:an"
        )

        response = await client.get("/v1/promotions/analytics", params={"days": 30})
        assert response.status_code == 200
        body = response.json()
        assert body["total_promotions"] >= 1
        assert body["total_spend_cents"] >= promotion.amount_cents
        assert "ctr" in body
        assert isinstance(body["periods"], list)

    @pytest.mark.auth
    async def test_count_excludes_unpaid_drafts(
        self,
        client: AsyncClient,
        session: AsyncSession,
        user: User,
        mocker: MockerFixture,
    ) -> None:
        mocker.patch.object(settings, "is_tinybird_configured", return_value=False)
        paid = await _make_pending(session, user)
        await promotion_service.activate_paid(
            session, paid.id, external_ref="order:paid"
        )
        # An abandoned checkout: created but never confirmed by the webhook.
        await _make_pending(session, user)

        response = await client.get("/v1/promotions/analytics")
        body = response.json()
        assert body["total_promotions"] == 1
        assert body["total_spend_cents"] == paid.amount_cents
