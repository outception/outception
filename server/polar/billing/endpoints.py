from typing import Any

from fastapi import Depends, HTTPException, Request
from standardwebhooks.webhooks import Webhook as StandardWebhook

from polar.config import settings
from polar.postgres import AsyncSession, get_db_session
from polar.routing import APIRouter

from .service import billing as billing_service

router = APIRouter(prefix="/billing", tags=["billing"])

# The gateway sends Standard Webhooks headers (webhook-*); some senders use svix-*.
_SVIX_TO_STANDARD = {
    "svix-id": "webhook-id",
    "svix-timestamp": "webhook-timestamp",
    "svix-signature": "webhook-signature",
}


def _remap_headers(headers: dict[str, str]) -> dict[str, str]:
    return {_SVIX_TO_STANDARD.get(k.lower(), k.lower()): v for k, v in headers.items()}


def _verify_webhook(raw_body: bytes, headers: dict[str, str]) -> Any | None:
    secret = settings.PAYMENT_GATEWAY_WEBHOOK_SECRET
    if not secret:
        raise HTTPException(status_code=500)
    if secret.startswith("whsec_"):
        secret = secret[6:]
    try:
        return StandardWebhook(secret).verify(raw_body, _remap_headers(headers))
    except Exception:
        return None


@router.post("/webhook", status_code=202, include_in_schema=False)
async def webhook(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, bool]:
    """Receive gateway webhooks. One-time `order.*` events activate the paid
    promotion they reference (filtered by checkout metadata inside the handler)."""
    raw_body = await request.body()
    event = _verify_webhook(raw_body, dict(request.headers))
    if event is None:
        raise HTTPException(status_code=403)
    event_type = str(event.get("type", ""))
    if event_type.startswith("order."):
        await billing_service.handle_promotion_purchase(
            session, data=event.get("data", {})
        )
    return {"received": True}
