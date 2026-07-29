"""Fun daily feeds — Jokes and Quotes of the day — from free, no-auth APIs.

Unlike the scraper sources these build ``NewsItem`` rows directly from a JSON
API rather than an RSS feed.
"""

from typing import Any

from ..fetch import NewsFetchError, fetch_json
from ..registry import register
from ..schemas import NewsItem

_JOKES_URL = (
    "https://v2.jokeapi.dev/joke/Any"
    "?safe-mode&type=twopart&amount=10&blacklistFlags=nsfw,religious,political,racist,sexist,explicit"
)
_QUOTES_URL = "https://zenquotes.io/api/quotes"
_BIBLE_URL = "https://labs.bible.org/api/?passage=random&type=json&count=15"


async def _jokes() -> list[NewsItem]:
    data: Any = await fetch_json(_JOKES_URL)
    raw = data.get("jokes") if isinstance(data, dict) else None
    if not raw:
        raise NewsFetchError("no jokes returned")
    items: list[NewsItem] = []
    for joke in raw:
        setup = joke.get("setup", "").strip()
        delivery = joke.get("delivery", "").strip()
        if not setup or not delivery:
            continue
        items.append(
            NewsItem(
                id=f"joke-{joke.get('id', len(items))}",
                title=f"{setup} … {delivery}",
                url="https://jokeapi.dev",
            )
        )
    if not items:
        raise NewsFetchError("no usable jokes")
    return items


async def _quotes() -> list[NewsItem]:
    data: Any = await fetch_json(_QUOTES_URL)
    if not isinstance(data, list) or not data:
        raise NewsFetchError("no quotes returned")
    items: list[NewsItem] = []
    for i, quote in enumerate(data):
        text = (quote.get("q") or "").strip()
        author = (quote.get("a") or "Unknown").strip()
        if not text:
            continue
        items.append(
            NewsItem(
                id=f"quote-{i}",
                title=f"“{text}” — {author}",
                url="https://zenquotes.io",
            )
        )
    if not items:
        raise NewsFetchError("no usable quotes")
    return items


async def _bible() -> list[NewsItem]:
    data: Any = await fetch_json(_BIBLE_URL)
    if not isinstance(data, list) or not data:
        raise NewsFetchError("no verses returned")
    items: list[NewsItem] = []
    for i, verse in enumerate(data):
        text = (verse.get("text") or "").strip()
        book = (verse.get("bookname") or "").strip()
        ref = f"{book} {verse.get('chapter', '')}:{verse.get('verse', '')}".strip()
        if not text:
            continue
        items.append(
            NewsItem(
                id=f"bible-{i}",
                title=f"{text} — {ref}" if ref else text,
                url="https://bible.org",
            )
        )
    if not items:
        raise NewsFetchError("no usable verses")
    return items


register("jokes", _jokes)
register("quotes", _quotes)
register("bible", _bible)
