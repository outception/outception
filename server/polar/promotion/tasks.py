from typing import Any

from polar.integrations.tinybird import tinybird_client
from polar.worker import TaskPriority, actor

from .events import PROMOTION_EVENTS_DATASOURCE


@actor(actor_name="promotion.emit_events", priority=TaskPriority.LOW)
async def promotion_emit_events(events: list[dict[str, Any]]) -> None:
    await tinybird_client.send_events(PROMOTION_EVENTS_DATASOURCE, events)
