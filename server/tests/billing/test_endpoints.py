import json
from typing import Any

import pytest
from httpx import AsyncClient
from pytest_mock import MockerFixture
from standardwebhooks.webhooks import Webhook as StandardWebhook

from polar.config import settings
from polar.kit.utils import utc_now
from polar.models import User
from polar.models.promotion import Promotion, PromotionStatus
from polar.postgres import AsyncSession
from polar.promotion.repository import PromotionRepository
from polar.promotion.service import promotion as promotion_service

# A valid base64-encoded Standard Webhooks secret (no `whsec_` prefix).
WEBHOOK_SECRET = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="


def _signed_headers(
    payload: dict[str, Any], *, secret: str = WEBHOOK_SECRET
) -> tuple[bytes, dict[str, str]]:
    body = json.dumps(payload).encode()
    msg_id = "msg_test_1"
    timestamp = utc_now()
    signature = StandardWebhook(secret).sign(msg_id, timestamp, body.decode())
    headers = {
        "webhook-id": msg_id,
        "webhook-timestamp": str(int(timestamp.timestamp())),
        "webhook-signature": signature,
        "content-type": "application/json",
    }
    return body, headers


async def _make_pending(session: AsyncSession, user: User) -> Promotion:
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
class TestWebhook:
    async def test_rejects_unsigned(
        self, client: AsyncClient, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "PAYMENT_GATEWAY_WEBHOOK_SECRET", WEBHOOK_SECRET)
        response = await client.post(
            "/v1/billing/webhook",
            content=json.dumps({"type": "order.paid"}).encode(),
            headers={"content-type": "application/json"},
        )
        assert response.status_code == 403

    async def test_rejects_bad_signature(
        self, client: AsyncClient, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "PAYMENT_GATEWAY_WEBHOOK_SECRET", WEBHOOK_SECRET)
        body, headers = _signed_headers({"type": "order.paid"})
        headers["webhook-signature"] = "v1,deadbeef"
        response = await client.post(
            "/v1/billing/webhook", content=body, headers=headers
        )
        assert response.status_code == 403

    async def test_missing_secret_is_500(
        self, client: AsyncClient, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "PAYMENT_GATEWAY_WEBHOOK_SECRET", "")
        body, headers = _signed_headers({"type": "order.paid"})
        response = await client.post(
            "/v1/billing/webhook", content=body, headers=headers
        )
        assert response.status_code == 500

    async def test_activates_promotion_on_order_paid(
        self,
        client: AsyncClient,
        session: AsyncSession,
        user: User,
        mocker: MockerFixture,
    ) -> None:
        mocker.patch.object(settings, "PAYMENT_GATEWAY_WEBHOOK_SECRET", WEBHOOK_SECRET)
        promotion = await _make_pending(session, user)
        payload = {
            "type": "order.paid",
            "data": {
                "id": "order_abc",
                "status": "paid",
                "total_amount": promotion.amount_cents,
                "metadata": {
                    "kind": "promotion_purchase",
                    "user_id": str(user.id),
                    "promotion_id": str(promotion.id),
                },
            },
        }
        body, headers = _signed_headers(payload)

        response = await client.post(
            "/v1/billing/webhook", content=body, headers=headers
        )
        assert response.status_code == 202
        assert response.json() == {"received": True}

        repo = PromotionRepository.from_session(session)
        refreshed = await repo.get_by_id(promotion.id)
        assert refreshed is not None
        # Empty category → promoted straight to ACTIVE.
        assert refreshed.status == PromotionStatus.ACTIVE
        assert refreshed.payment_ref == "order:order_abc"

    @pytest.mark.parametrize(
        "data_extra",
        [
            pytest.param({"total_amount": 1}, id="underpaid"),
            pytest.param({}, id="no_amount_field"),
        ],
    )
    async def test_underpaid_or_amountless_order_is_refused(
        self,
        client: AsyncClient,
        session: AsyncSession,
        user: User,
        mocker: MockerFixture,
        data_extra: dict[str, Any],
    ) -> None:
        mocker.patch.object(settings, "PAYMENT_GATEWAY_WEBHOOK_SECRET", WEBHOOK_SECRET)
        promotion = await _make_pending(session, user)
        assert promotion.amount_cents > 1
        payload = {
            "type": "order.paid",
            "data": {
                "id": "order_cheap",
                "status": "paid",
                **data_extra,
                "metadata": {
                    "kind": "promotion_purchase",
                    "user_id": str(user.id),
                    "promotion_id": str(promotion.id),
                },
            },
        }
        body, headers = _signed_headers(payload)

        response = await client.post(
            "/v1/billing/webhook", content=body, headers=headers
        )
        assert response.status_code == 202

        repo = PromotionRepository.from_session(session)
        refreshed = await repo.get_by_id(promotion.id)
        assert refreshed is not None
        assert refreshed.status == PromotionStatus.PENDING_PAYMENT

    async def test_real_polar_order_shape_uses_gross_total_amount(
        self,
        client: AsyncClient,
        session: AsyncSession,
        user: User,
        mocker: MockerFixture,
    ) -> None:
        # A real polar.sh order carries subtotal/tax/total/net. The customer
        # paid `total_amount` (gross); `net_amount` is lower because Polar's fee
        # is deducted. The check must accept on the gross total, not refuse just
        # because the merchant nets less than the slot price after fees.
        mocker.patch.object(settings, "PAYMENT_GATEWAY_WEBHOOK_SECRET", WEBHOOK_SECRET)
        promotion = await _make_pending(session, user)
        price = promotion.amount_cents
        payload = {
            "type": "order.paid",
            "data": {
                "id": "order_real_shape",
                "status": "paid",
                "currency": "usd",
                "subtotal_amount": price,
                "discount_amount": 0,
                "tax_amount": 0,
                "total_amount": price,  # what the customer was charged
                "net_amount": price - 50,  # after Polar's fee — intentionally < price
                "metadata": {
                    "kind": "promotion_purchase",
                    "user_id": str(user.id),
                    "promotion_id": str(promotion.id),
                },
            },
        }
        body, headers = _signed_headers(payload)

        response = await client.post(
            "/v1/billing/webhook", content=body, headers=headers
        )
        assert response.status_code == 202

        repo = PromotionRepository.from_session(session)
        refreshed = await repo.get_by_id(promotion.id)
        assert refreshed is not None
        # Activated despite net_amount < price — the gross total covered the slot.
        assert refreshed.status == PromotionStatus.ACTIVE
        assert refreshed.payment_ref == "order:order_real_shape"

    async def test_ignores_non_promotion_order(
        self,
        client: AsyncClient,
        session: AsyncSession,
        user: User,
        mocker: MockerFixture,
    ) -> None:
        mocker.patch.object(settings, "PAYMENT_GATEWAY_WEBHOOK_SECRET", WEBHOOK_SECRET)
        promotion = await _make_pending(session, user)
        payload = {
            "type": "order.paid",
            "data": {
                "id": "order_other",
                "status": "paid",
                "metadata": {"kind": "something_else"},
            },
        }
        body, headers = _signed_headers(payload)

        response = await client.post(
            "/v1/billing/webhook", content=body, headers=headers
        )
        assert response.status_code == 202

        repo = PromotionRepository.from_session(session)
        refreshed = await repo.get_by_id(promotion.id)
        assert refreshed is not None
        assert refreshed.status == PromotionStatus.PENDING_PAYMENT

    async def test_non_order_event_is_noop(
        self,
        client: AsyncClient,
        mocker: MockerFixture,
    ) -> None:
        mocker.patch.object(settings, "PAYMENT_GATEWAY_WEBHOOK_SECRET", WEBHOOK_SECRET)
        handler = mocker.patch.object(promotion_service, "activate_paid", autospec=True)
        body, headers = _signed_headers({"type": "customer.updated", "data": {}})

        response = await client.post(
            "/v1/billing/webhook", content=body, headers=headers
        )
        assert response.status_code == 202
        handler.assert_not_called()
