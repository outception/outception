"""The Products of the day card: a feed whose items come from the launch
service's card entry instead of an upstream. The service writes the
entry on every change; this adapter only reads it, and falls back to the
house line alone when nothing has been written yet."""

import json
from datetime import UTC, datetime

from outception.redis import Redis, create_redis

from ..registry import register
from ..schemas import NewsItem

SOURCE_ID = "products-of-the-day"
CARD_ITEMS_KEY = "launches:card:items"

_redis: Redis | None = None


def _client() -> Redis:
    global _redis
    if _redis is None:
        _redis = create_redis("app")
    return _redis


async def products_of_the_day() -> list[NewsItem]:
    raw = await _client().get(CARD_ITEMS_KEY)
    if raw is not None:
        try:
            return [NewsItem.model_validate(item) for item in json.loads(raw)]
        except ValueError, TypeError:
            pass
    from outception.launches.service import house_item

    return [house_item(datetime.now(UTC).date())]


register(SOURCE_ID, products_of_the_day)
