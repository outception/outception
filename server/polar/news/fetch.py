"""Outbound fetch helpers for news source scrapers.

One shared ``httpx.AsyncClient`` with a browser User-Agent (several of
the scraped sites 403 obvious bot UAs), retries, and a body-size cap.
Every fetch is gated by the same SSRF guard the link-preview worker
uses — scraper URLs are hardcoded per source, but the guard costs
little and keeps the public endpoints safe-by-construction.
"""

import calendar
from typing import Any

import feedparser
import httpx
import structlog
from bs4 import BeautifulSoup

from polar.link_preview.extractor import is_fetchable

from .schemas import NewsItem

log = structlog.get_logger()

_MAX_BYTES = 5 * 1024 * 1024  # 5 MB — healthy feeds range up to ~4 MB (UK roads events)
_TIMEOUT_SECONDS = 10.0
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)

_client = httpx.AsyncClient(
    follow_redirects=True,
    timeout=_TIMEOUT_SECONDS,
    max_redirects=5,
    headers={
        "User-Agent": _USER_AGENT,
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
    },
    transport=httpx.AsyncHTTPTransport(retries=2),
)


class NewsFetchError(Exception):
    """A source fetch failed (bad URL, HTTP error, oversized body)."""


async def _get(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
) -> httpx.Response:
    if not is_fetchable(url):
        raise NewsFetchError(f"unsafe or unresolvable URL: {url}")
    try:
        response = await _client.get(url, headers=headers, params=params)
    except httpx.HTTPError as exc:
        raise NewsFetchError(f"fetch failed: {exc}") from exc
    if response.status_code >= 400:
        raise NewsFetchError(f"HTTP {response.status_code} from {url}")
    if len(response.content) > _MAX_BYTES:
        raise NewsFetchError(f"body too large from {url}")
    return response


async def fetch_text(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    encoding: str | None = None,
) -> str:
    response = await _get(url, headers=headers, params=params)
    try:
        return response.content.decode(
            encoding or response.encoding or "utf-8", errors="replace"
        )
    except (LookupError, ValueError):
        return response.content.decode("utf-8", errors="replace")


async def fetch_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
) -> Any:
    response = await _get(url, headers=headers, params=params)
    try:
        return response.json()
    except ValueError as exc:
        raise NewsFetchError(f"invalid JSON from {url}") from exc


async def fetch_html(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    encoding: str | None = None,
) -> BeautifulSoup:
    """Fetch and parse an HTML page. Pass ``encoding`` (e.g. ``gb2312``)
    for legacy-encoded pages — decoding happens from raw bytes so the
    declared charset wins over httpx's guess."""
    response = await _get(url, headers=headers, params=params)
    return BeautifulSoup(response.content, "lxml", from_encoding=encoding)


def parse_rss(text: str, *, limit: int = 30) -> list[NewsItem]:
    """Map an RSS/Atom feed into news items (shared by every RSS-backed
    source — mirrors the upstream RSS factory)."""
    feed = feedparser.parse(text)
    items: list[NewsItem] = []
    # Some feeds emit the same entry twice (e.g. BBC Sport) — dedupe by
    # link so downstream consumers can key on the id safely.
    seen: set[str] = set()
    for entry in feed.entries[:limit]:
        link = entry.get("link")
        title = entry.get("title")
        if not link or not title:
            continue
        if link in seen:
            continue
        seen.add(link)
        pub_date: int | None = None
        parsed = entry.get("published_parsed") or entry.get("updated_parsed")
        if parsed is not None:
            pub_date = calendar.timegm(parsed) * 1000
        items.append(NewsItem(id=link, title=title, url=link, pub_date=pub_date))
    return items
