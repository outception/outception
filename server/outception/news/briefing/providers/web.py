"""Web push: the browser's push service, VAPID-signed, payload encrypted
to the subscription's keys."""

import json
from typing import Any

import structlog
from pywebpush import WebPushException, webpush

from outception.config import settings

from . import Outcome

log = structlog.get_logger()

GONE = {404, 410}


def configured() -> bool:
    return bool(
        settings.WEB_PUSH_VAPID_PRIVATE_KEY
        and settings.WEB_PUSH_VAPID_PUBLIC_KEY
        and settings.WEB_PUSH_SUBJECT
    )


def send(
    endpoint: str, keys: dict[str, Any] | None, message: dict[str, Any]
) -> Outcome:
    """Blocking; the caller runs it in a thread."""
    if not configured() or not keys:
        return "failed"
    try:
        webpush(
            subscription_info={"endpoint": endpoint, "keys": keys},
            data=json.dumps(message, ensure_ascii=False),
            vapid_private_key=settings.WEB_PUSH_VAPID_PRIVATE_KEY,
            vapid_claims={"sub": settings.WEB_PUSH_SUBJECT},
            ttl=12 * 3600,
            timeout=10,
        )
    except WebPushException as exc:
        status = getattr(exc.response, "status_code", None)
        if status in GONE:
            return "gone"
        log.info("push.web.failed", status=status, error=str(exc)[:200])
        return "failed"
    except Exception as exc:
        log.info("push.web.failed", error=str(exc)[:200])
        return "failed"
    return "delivered"
