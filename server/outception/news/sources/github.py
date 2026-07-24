"""GitHub Trending (today)."""

from ..fetch import fetch_html
from ..registry import register
from ..schemas import NewsExtra, NewsItem

_BASE = "https://github.com"
_URL = "https://github.com/trending?spoken_language_code="


async def github_trending() -> list[NewsItem]:
    soup = await fetch_html(_URL)
    items: list[NewsItem] = []
    for el in soup.select("main .Box div[data-hpc] > article"):
        a = el.select_one(":scope > h2 a")
        if a is None:
            continue
        href = a.get("href")
        title = " ".join(a.get_text().split())
        if not href or not title:
            continue
        star_el = el.select_one("[href$=stargazers]")
        star = "".join(star_el.get_text().split()) if star_el else ""
        desc_el = el.select_one(":scope > p")
        desc = " ".join(desc_el.get_text().split()) if desc_el else ""
        items.append(
            NewsItem(
                id=str(href),
                title=title,
                url=f"{_BASE}{href}",
                extra=NewsExtra(info=f"✰ {star}", hover=desc or None),
            )
        )
    return items


register("github", github_trending)
register("github-trending-today", github_trending)
