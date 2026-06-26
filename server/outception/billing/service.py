from typing import Any
from uuid import UUID

import structlog

from outception.auth.models import AuthSubject, User
from outception.config import settings
from outception.logging import Logger
from outception.postgres import AsyncSession

from .client import payment_gateway_client

log: Logger = structlog.get_logger()

# Order fields that may carry the amount the customer was charged, most
# authoritative first. ``total_amount`` is the gross charged (incl. tax), so it
# only ever exceeds the promotion price for a valid payment.
_ORDER_AMOUNT_FIELDS = ("total_amount", "amount", "subtotal_amount", "net_amount")


def _extract_paid_amount(data: dict[str, Any]) -> int | None:
    for field in _ORDER_AMOUNT_FIELDS:
        value = data.get(field)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    return None


class BillingService:
    """Payment-gateway integration for one-off promotion purchases."""

    async def create_promotion_checkout(
        self,
        auth_subject: AuthSubject[User],
        *,
        promotion_id: UUID,
        amount_cents: int,
    ) -> str:
        """Hosted checkout for a one-time promotion purchase. We stamp the buyer
        and the draft promotion id into the checkout metadata so the order
        webhook can activate exactly that promotion.

        Per-block pricing (``amount_cents`` = blocks × price) is honoured by
        passing ``amount`` to the polar.sh checkout; PROMOTION_PRODUCT_ID must be
        a pay-what-you-want product for the amount to apply."""
        user = auth_subject.subject
        return await payment_gateway_client.create_checkout(
            success_url=f"{settings.FRONTEND_BASE_URL}/?promotion=success",
            customer_external_id=str(user.id),
            customer_email=user.email,
            product_id=settings.PROMOTION_PRODUCT_ID,
            amount=amount_cents,
            metadata={
                "kind": "promotion_purchase",
                "user_id": str(user.id),
                "promotion_id": str(promotion_id),
                "amount_cents": str(amount_cents),
            },
        )

    async def handle_promotion_purchase(
        self, session: AsyncSession, *, data: dict[str, Any]
    ) -> None:
        """Activate a promotion on a completed order. Gated on our own
        ``kind == "promotion_purchase"`` metadata, so other orders are ignored.
        Idempotent: ``activate_paid`` keys on the order id, so a redelivered
        order.* event queues the promotion exactly once. The order must also
        report an amount that covers the promotion's price (the product is
        pay-what-you-want, so an underpaid order is refused, not activated)."""
        from outception.promotion.service import promotion as promotion_service

        metadata = data.get("metadata") or {}
        if metadata.get("kind") != "promotion_purchase":
            return

        status = str(data.get("status") or "").lower()
        if status and status not in ("paid", "completed", "succeeded"):
            return

        order_id = data.get("id")
        if not order_id:
            log.warning("billing.promotion.no_id", data_keys=sorted(data.keys()))
            return

        promotion_id_raw = metadata.get("promotion_id")
        if not promotion_id_raw:
            log.warning("billing.promotion.no_promotion_id", order_id=order_id)
            return
        try:
            promotion_id = UUID(str(promotion_id_raw))
        except ValueError:
            log.warning(
                "billing.promotion.bad_promotion_id", promotion_id=promotion_id_raw
            )
            return

        paid_amount_cents = _extract_paid_amount(data)
        if paid_amount_cents is None:
            log.warning(
                "billing.promotion.no_amount",
                order_id=order_id,
                data_keys=sorted(data.keys()),
            )
            return

        await promotion_service.activate_paid(
            session,
            promotion_id,
            external_ref=f"order:{order_id}",
            paid_amount_cents=paid_amount_cents,
        )


billing = BillingService()
