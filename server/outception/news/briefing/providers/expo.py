"""App push through the Expo push service: the app's device token is the
address, the payload is the same message the web gets."""

from typing import Any

import httpx
import structlog

from . import Outcome

log = structlog.get_logger()

PUSH_URL = "https://exp.host/--/api/v2/push/send"
GONE_ERRORS = {"DeviceNotRegistered"}


async def send(token: str, message: dict[str, Any]) -> Outcome:
    body = {
        "to": token,
        "title": message.get("title"),
        "body": message.get("body"),
        "data": {"url": message.get("url"), "profile": message.get("profile")},
        "sound": None,
        "priority": "default",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(PUSH_URL, json=body)
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        log.info("push.app.failed", error=str(exc)[:200])
        return "failed"
    ticket = (payload.get("data") or {}) if isinstance(payload, dict) else {}
    if ticket.get("status") == "ok":
        return "delivered"
    details = ticket.get("details") or {}
    if details.get("error") in GONE_ERRORS:
        return "gone"
    log.info("push.app.failed", status=response.status_code, ticket=str(ticket)[:200])
    return "failed"
