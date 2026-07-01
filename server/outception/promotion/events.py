import uuid
from typing import Any

from outception.config import settings
from outception.kit.utils import utc_now
from outception.models import Promotion
from outception.worker import enqueue_job

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
    """Enqueue a batch of pre-built promotion events for Tinybird ingestion.
    No-op when empty or when Tinybird isn't configured — skipping the enqueue
    keeps the hot path (an impression per public wall render) from queuing jobs
    the worker would only no-op. Postgres analytics counters are tallied
    separately, so nothing is lost when Tinybird is off."""
    if events and settings.is_tinybird_configured():
        enqueue_job("promotion.emit_events", events=events)
