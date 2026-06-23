import httpx

from polar.config import settings


class PaymentGatewayClient:
    """Thin client for the external payment gateway."""

    async def create_checkout(
        self,
        *,
        success_url: str,
        customer_external_id: str,
        customer_email: str,
        product_id: str,
        amount: int | None = None,
        metadata: dict[str, str] | None = None,
    ) -> str:
        """Create a polar.sh hosted checkout and return its URL. ``amount`` (in
        cents) sets the price for a pay-what-you-want product, which is how we
        honour per-block promotion pricing. ``metadata`` round-trips context
        back on the order webhook."""
        body: dict[str, object] = {
            "products": [product_id],
            "success_url": success_url,
            "external_customer_id": customer_external_id,
            "customer_email": customer_email,
        }
        if amount is not None:
            body["amount"] = amount
        if metadata is not None:
            body["metadata"] = metadata
        async with httpx.AsyncClient(
            base_url=settings.PAYMENT_GATEWAY_BASE_URL,
            headers={
                "Authorization": f"Bearer {settings.PAYMENT_GATEWAY_ACCESS_TOKEN}"
            },
            timeout=30.0,
        ) as client:
            response = await client.post("/v1/checkouts/", json=body)
            response.raise_for_status()
            return str(response.json()["url"])


payment_gateway_client = PaymentGatewayClient()
