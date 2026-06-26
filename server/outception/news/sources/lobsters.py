"""Lobsters — hottest stories (JSON API)."""

from ..fetch import fetch_json
from ..registry import source
from ..schemas import NewsExtra, NewsItem

_URL = "https://lobste.rs/hottest.json"


@source("lobsters")
async def lobsters() -> list[NewsItem]:
    data = await fetch_json(_URL)
    items: list[NewsItem] = []
    for entry in data:
        short_id = entry.get("short_id")
        title = entry.get("title")
        comments_url = entry.get("comments_url")
        score = entry.get("score")
        if not short_id or not title or not comments_url:
            continue
        items.append(
            NewsItem(
                id=short_id,
                title=title,
                url=comments_url,
                extra=NewsExtra(info=f"{score} points"),
            )
        )
    return items
