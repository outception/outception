"""Hacker News front page."""

from ..fetch import fetch_html
from ..registry import source
from ..schemas import NewsExtra, NewsItem

_BASE = "https://news.ycombinator.com"


@source("hackernews")
async def hackernews() -> list[NewsItem]:
    soup = await fetch_html(_BASE)
    items: list[NewsItem] = []
    for row in soup.select(".athing"):
        link = row.select_one(".titleline a")
        item_id = row.get("id")
        if link is None or not item_id:
            continue
        title = link.get_text(strip=True)
        if not title:
            continue
        score_el = soup.select_one(f"#score_{item_id}")
        score = score_el.get_text(strip=True) if score_el else None
        items.append(
            NewsItem(
                id=str(item_id),
                title=title,
                url=f"{_BASE}/item?id={item_id}",
                extra=NewsExtra(info=score),
            )
        )
    return items
