import httpx

from outception.config import settings
from outception.exceptions import NotPermitted

turnstile_client = httpx.AsyncClient(
    base_url="https://challenges.cloudflare.com/turnstile/v0"
)


async def verify_turnstile(token: str | None, remote_ip: str | None) -> None:
    """Reject the request unless the bot check passes. With no secret
    configured there is no check; with one, a missing token fails."""
    if not settings.TURNSTILE_SECRET:
        return
    if not token:
        raise NotPermitted("Turnstile verification failed")
    try:
        response = await turnstile_client.post(
            "/siteverify",
            data={
                "secret": settings.TURNSTILE_SECRET,
                "response": token,
                "remoteip": remote_ip or "",
            },
        )
        result = response.json()
    except httpx.HTTPError as e:
        raise NotPermitted("Turnstile verification failed") from e

    if not isinstance(result, dict) or result.get("success") is not True:
        raise NotPermitted("Turnstile verification failed")
