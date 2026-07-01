"""Mastodon — trending statuses from mastodon.social."""

from bs4 import BeautifulSoup

from ..fetch import fetch_json
from ..registry import source
from ..schemas import NewsExtra, NewsItem

_URL = "https://mastodon.social/api/v1/trends/statuses?limit=30"
_MAX_TITLE = 140


def _plain_text(html: str) -> str:
    """Strip HTML tags and return plain text, truncated to _MAX_TITLE chars."""
    text = BeautifulSoup(html, "lxml").get_text(" ", strip=True)
    if len(text) > _MAX_TITLE:
        text = text[:_MAX_TITLE] + "…"
    return text


@source("mastodon")
async def mastodon() -> list[NewsItem]:
    data = await fetch_json(_URL)
    items: list[NewsItem] = []
    for status in data:
        content = status.get("content", "")
        text = _plain_text(content) if content else ""
        if not text:
            continue
        items.append(
            NewsItem(
                id=status["id"],
                title=text,
                url=status["url"],
                extra=NewsExtra(info=f"{status.get('favourites_count', 0)} favs"),
            )
        )
    return items
