import uuid
from typing import Any

from polar.kit.utils import utc_now
from polar.models import Promotion
from polar.worker import enqueue_job

PROMOTION_EVENTS_DATASOURCE = "promotion_events"
PROMOTION_ANALYTICS_PIPE = "promotion_analytics"


class PromotionEventName:
    created = "promotion_created"
    paid = "promotion_paid"
    activated = "promotion_activated"
    expired = "promotion_expired"
    impression = "promotion_impression"
    click = "promotion_click"


def build_event(promotion: Promotion, name: str) -> dict[str, Any]:
    """Build a JSON-serialisable promotion event for Tinybird ingestion."""
    return {
        "id": str(uuid.uuid4()),
        "timestamp": utc_now().isoformat(),
        "name": name,
        "promotion_id": str(promotion.id),
        "author_id": str(promotion.author_id),
        "category": promotion.category,
        "status": promotion.status,
        "amount_cents": promotion.amount_cents,
        "duration_minutes": promotion.duration_minutes,
    }


def emit(promotion: Promotion, name: str) -> None:
    """Enqueue a single promotion event for asynchronous Tinybird ingestion."""
    emit_many([build_event(promotion, name)])


def emit_many(events: list[dict[str, Any]]) -> None:
    """Enqueue a batch of pre-built promotion events. No-op when empty; the
    worker task is itself a no-op when Tinybird isn't configured."""
    if events:
        enqueue_job("promotion.emit_events", events=events)
