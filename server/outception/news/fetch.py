"""Outbound fetch helpers for news source scrapers.

One shared ``httpx.AsyncClient`` with a browser User-Agent (several of
the scraped sites 403 obvious bot UAs), retries, and a body-size cap.
Every fetch is gated by the same SSRF guard the link-preview worker
uses - scraper URLs are hardcoded per source, but the guard costs
little and keeps the public endpoints safe-by-construction.
"""

import asyncio
import calendar
import html
import ipaddress
import json
from typing import Any

import feedparser
import httpx
import structlog
from bs4 import BeautifulSoup

from outception.link_preview.extractor import is_fetchable_async

from .schemas import NewsItem

log = structlog.get_logger()

_MAX_BYTES = 5 * 1024 * 1024  # 5 MB - healthy feeds range up to ~4 MB (UK roads events)
_TIMEOUT_SECONDS = 10.0
# Total time one source fetch may take. httpx's timeout is per operation and the
# transport retries, so a drip-feeding upstream outlasts it; this is the bound
# that actually releases the slot. Proven on the worker after a hung scraper in
# prod on 2026-08-14, and shared so the request path can't drift tighter.
FETCH_TIMEOUT_SECONDS = 20.0
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)


class NewsFetchError(Exception):
    """A source fetch failed (bad URL, HTTP error, oversized body)."""


class StaleFeedError(NewsFetchError):
    """The feed still answers, but everything in it predates the staleness
    horizon. A publisher can abandon a feed without taking it down: it keeps
    returning 200 and a well-formed body, so a fetch that only checks for
    items happily re-caches years-old headlines forever."""


class UnsafeURLError(NewsFetchError):
    """The SSRF guard refused the URL, the redirect target, or the socket's
    real peer. A distinct type because callers branch on it - the reader
    fallback must never forward a guard-refused URL to the hosted fetcher -
    and matching the message prefix instead meant any reword of these errors
    silently opened that path."""


def _peer_address(response: httpx.Response) -> str | None:
    """The address we actually connected to, straight from the socket."""
    stream = response.extensions.get("network_stream")
    if stream is None:
        return None
    sock = stream.get_extra_info("socket")
    if sock is None:
        return None
    try:
        peer = sock.getpeername()
    except OSError:
        return None
    return str(peer[0]) if peer else None


def _reject_private_peer(response: httpx.Response) -> None:
    """The guard resolves the host, then httpx resolves it again when it
    connects. A hostile resolver can answer differently the second time -
    public once to pass the guard, then 127.0.0.1 - so the name alone proves
    nothing. Checking the socket's real peer closes that window, and it runs
    before any of the body is read, so nothing internal can be read back.

    Unknown peers (a transport without a socket, as in tests) are left to the
    name-based guard rather than failing the fetch."""
    peer = _peer_address(response)
    if peer is None:
        return
    try:
        ip = ipaddress.ip_address(peer)
    except ValueError:
        return
    if not ip.is_global:
        # Query stripped: these messages reach logs/Sentry, and several
        # upstreams carry API keys in the query string.
        raise UnsafeURLError(
            f"unsafe peer address {peer} for {response.url.copy_with(query=None)}"
        )


async def _vet_response(response: httpx.Response) -> None:
    """Re-apply the SSRF guard to every hop: the address actually connected to,
    and - for a redirect - the URL it points at. ``is_fetchable`` only vets the
    initial URL, but ``follow_redirects`` would otherwise let a source bounce us
    to an internal address (e.g. the cloud metadata IP)."""
    _reject_private_peer(response)
    if response.is_redirect:
        location = response.headers.get("location", "")
        try:
            target = str(response.url.join(location))
        except httpx.InvalidURL as exc:
            raise NewsFetchError(f"invalid redirect URL: {exc}") from exc
        if not await is_fetchable_async(target):
            raise UnsafeURLError(f"unsafe redirect to {target}")


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
    event_hooks={"response": [_vet_response]},
)


async def _get(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
) -> tuple[bytes, str | None]:
    """Fetch a URL and return ``(body, charset)``: the decoded body bytes and
    the charset declared in the response's Content-Type (or ``None``).

    Streams so the size cap is enforced as bytes arrive rather than buffering
    a possibly-huge (or length-lying) body first. ``aiter_bytes`` decodes the
    transfer/content encoding, so the returned bytes are already decompressed.
    """
    if not await is_fetchable_async(url):
        raise UnsafeURLError(f"unsafe or unresolvable URL: {url}")
    try:
        async with _client.stream(
            "GET", url, headers=headers, params=params
        ) as response:
            if response.status_code >= 400:
                raise NewsFetchError(f"HTTP {response.status_code} from {url}")
            body = bytearray()
            async for chunk in response.aiter_bytes():
                body.extend(chunk)
                if len(body) > _MAX_BYTES:
                    raise NewsFetchError(f"body too large from {url}")
            return bytes(body), response.charset_encoding
    except httpx.HTTPError as exc:
        raise NewsFetchError(f"fetch failed: {exc}") from exc


async def fetch_text(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    encoding: str | None = None,
) -> str:
    content, charset = await _get(url, headers=headers, params=params)
    try:
        return content.decode(encoding or charset or "utf-8", errors="replace")
    except LookupError:
        # Unknown charset name - fall back to utf-8.
        return content.decode("utf-8", errors="replace")


async def fetch_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
) -> Any:
    content, _ = await _get(url, headers=headers, params=params)
    try:
        return json.loads(content)
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
    for legacy-encoded pages - decoding happens from raw bytes so the
    declared charset wins over httpx's guess."""
    content, _ = await _get(url, headers=headers, params=params)
    # lxml parsing of a multi-MB page is CPU-bound: keep it off the event loop.
    return await asyncio.to_thread(
        BeautifulSoup, content, "lxml", from_encoding=encoding
    )


async def parse_rss_async(text: str, *, limit: int = 30) -> list[NewsItem]:
    """``parse_rss`` for getters: feedparser is pure CPU and a large feed
    would otherwise stall every other request for its whole parse."""
    return await asyncio.to_thread(parse_rss, text, limit=limit)


def parse_rss(text: str, *, limit: int = 30) -> list[NewsItem]:
    """Map an RSS/Atom feed into news items (shared by every RSS-backed
    source - mirrors the upstream RSS factory)."""
    feed = feedparser.parse(text)
    items: list[NewsItem] = []
    # Some feeds emit the same entry twice (e.g. BBC Sport) - dedupe by
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
        # Some feeds (e.g. The Verge) double-encode entities, so feedparser
        # leaves numeric ones like &#8217; in the title - decode them so the
        # headline (and its machine translation) reads cleanly. Decoding can
        # RESURRECT markup ("&amp;lt;b&amp;gt;" becomes "<b>"), so tags are
        # stripped after, and a malformed feed that emits its whole body as
        # the title is capped rather than rendered as a wall of text.
        title = html.unescape(title)
        if "<" in title:
            title = BeautifulSoup(title, "lxml").get_text(" ")
        title = " ".join(title.split())
        if not title:
            continue
        if len(title) > _MAX_TITLE_CHARS:
            cut = title.rfind(" ", 0, _MAX_TITLE_CHARS)
            title = title[: cut if cut > 100 else _MAX_TITLE_CHARS] + "…"
        items.append(
            NewsItem(
                id=link,
                title=title,
                url=link,
                pub_date=pub_date,
                teaser=_entry_teaser(entry, title, link),
            )
        )
    return items


_TEASER_MIN_CHARS = 40
_TEASER_MAX_CHARS = 400
# Above any real headline; a feed that blows past it put its article body in
# <title> and would otherwise ship a wall of text to the card, the translator
# (whose request schema caps at 512) and the search index.
_MAX_TITLE_CHARS = 300


def _entry_teaser(entry: object, title: str, link: str) -> str | None:
    """The publisher's standfirst for a feed entry as plain text, or None when
    the feed carries nothing worth showing (no description, a repeat of the
    headline, or Google News' link lists)."""
    if "news.google.com" in link:
        return None
    get = getattr(entry, "get", None)
    raw = (get("summary") or get("description") or "") if get else ""
    if not raw:
        return None
    # Unescape FIRST: on double-encoded feeds the tags are still entities when
    # the parser runs, so stripping before unescaping handed the reader
    # literal "<p>…</p>" around the standfirst.
    text = BeautifulSoup(html.unescape(raw), "lxml").get_text(" ")
    text = " ".join(text.split())
    if len(text) < _TEASER_MIN_CHARS or text.casefold() == title.casefold():
        return None
    if len(text) > _TEASER_MAX_CHARS:
        cut = text.rfind(" ", 0, _TEASER_MAX_CHARS)
        text = text[: cut if cut > _TEASER_MIN_CHARS else _TEASER_MAX_CHARS] + "…"
    return text
