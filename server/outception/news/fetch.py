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
import zlib
from collections.abc import Iterable
from typing import Any

import feedparser
import httpcore
import httpx
import structlog
from bs4 import BeautifulSoup

from outception.net.guard import is_fetchable_async, resolve_global_async

from .clusters.urlkey import url_key
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
    cutoff. A publisher can abandon a feed without taking it down: it keeps
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
            raise UnsafeURLError(
                f"unsafe redirect to {httpx.URL(str(target)).copy_with(query=None)}"
            )


class _PinnedRefusal(httpcore.UnsupportedProtocol):
    """The pinned connect found the name resolving outside public space.
    httpx wraps it in its own error; `_get` looks for it in the cause and
    raises UnsafeURLError, so a refusal never reads as an ordinary failure
    (which would send the URL on to the hosted reader)."""


class _PinnedBackend(httpcore.AnyIOBackend):
    """Resolve at connect time, through the guard, and connect to the
    vetted address. The connection pool keeps the hostname as its key (so a
    shared edge address never serves one host's connection to another), TLS
    still verifies the hostname, and the socket goes where the check looked:
    a name that re-resolves to an internal address between the guard and
    the connect is refused here, before a byte of the request leaves."""

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[Any] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        addresses = await resolve_global_async(host)
        if not addresses:
            # Not a ConnectError: the pool retries those, and a refusal is
            # final. UnsupportedProtocol maps to an httpx error the fetch
            # turns into NewsFetchError like any other failure.
            raise _PinnedRefusal(f"refused: {host} is not a global address")
        # IPv4 first: a dual-stack host from a container without a v6 route
        # would otherwise spend the whole timeout on the AAAA answer.
        ordered = sorted(addresses, key=lambda address: ":" in address)
        failure: Exception | None = None
        for address in ordered:
            try:
                return await super().connect_tcp(
                    address,
                    port,
                    timeout=timeout,
                    local_address=local_address,
                    socket_options=socket_options,
                )
            except (httpcore.ConnectError, httpcore.ConnectTimeout) as exc:
                failure = exc
        raise failure if failure is not None else httpcore.ConnectError(host)


def pinned_transport(retries: int = 2) -> httpx.AsyncHTTPTransport:
    """An httpx transport whose connections go through the pinned backend.
    The pool is swapped under the stock transport: httpx exposes no backend
    argument, and the pool is the only thing the transport wraps."""
    transport = httpx.AsyncHTTPTransport(retries=retries)
    limits = httpx.Limits()
    transport._pool = httpcore.AsyncConnectionPool(
        ssl_context=httpx.create_ssl_context(),
        max_connections=limits.max_connections,
        max_keepalive_connections=limits.max_keepalive_connections,
        keepalive_expiry=limits.keepalive_expiry,
        retries=retries,
        network_backend=_PinnedBackend(),
    )
    return transport


_client = httpx.AsyncClient(
    # No proxy from the environment: a proxy transport would bypass the
    # pinned connect, so every pinned client says so.
    trust_env=False,
    follow_redirects=True,
    timeout=_TIMEOUT_SECONDS,
    max_redirects=5,
    headers={
        "User-Agent": _USER_AGENT,
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        # Plain bodies only: a compressed response inflates in memory before
        # the byte cap can see it, so the cap bounds exactly what arrives.
        "Accept-Encoding": "identity",
    },
    transport=pinned_transport(),
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
    a possibly-huge (or length-lying) body first. We ask for plain bodies,
    but a server may compress anyway: the raw bytes are inflated here, a
    bounded piece at a time, so a small compressed bomb hits the cap long
    before it fills memory. An encoding we cannot bound is refused.
    """
    if not await is_fetchable_async(url):
        raise UnsafeURLError(f"unsafe or unresolvable URL: {url}")
    try:
        async with _client.stream(
            "GET", url, headers=headers, params=params
        ) as response:
            if response.status_code >= 400:
                raise NewsFetchError(f"HTTP {response.status_code} from {url}")
            encoding = response.headers.get("content-encoding", "").strip().lower()
            if encoding in _UNBOUNDED or "," in encoding:
                raise NewsFetchError(f"unsupported encoding {encoding!r} from {url}")
            # An unknown label is read as plain, as the client always did.
            inflater = (
                zlib.decompressobj(zlib.MAX_WBITS | 32)
                if encoding in _INFLATE
                else None
            )
            body = bytearray()
            async for chunk in response.aiter_raw():
                room = _MAX_BYTES - len(body)
                body.extend(
                    chunk if inflater is None else _inflate(inflater, chunk, room)
                )
                if len(body) > _MAX_BYTES:
                    raise NewsFetchError(f"body too large from {url}")
            return bytes(body), response.charset_encoding
    except httpx.HTTPError as exc:
        if _refused(exc):
            raise UnsafeURLError(f"refused at connect: {url}") from exc
        raise NewsFetchError(f"fetch failed: {exc}") from exc
    except zlib.error as exc:
        raise NewsFetchError(f"bad compressed body from {url}") from exc


# Compressed bodies zlib inflates in bounded steps, and the ones it cannot,
# which are refused rather than inflated whole.
_INFLATE = frozenset({"gzip", "x-gzip", "deflate"})
_UNBOUNDED = frozenset({"br", "zstd", "compress", "x-compress"})


def _inflate(inflater: Any, chunk: bytes, room: int) -> bytes:
    """What `chunk` inflates to, never much more than `room` bytes: one byte
    past it is enough for the caller to see the cap is broken."""
    out = bytearray()
    data = chunk
    while True:
        out.extend(inflater.decompress(data, room - len(out) + 1))
        data = inflater.unconsumed_tail
        if not data or len(out) > room:
            return bytes(out)


def _refused(exc: BaseException) -> bool:
    cause: BaseException | None = exc
    while cause is not None:
        if isinstance(cause, _PinnedRefusal):
            return True
        cause = cause.__cause__ or cause.__context__
    return False


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


async def fetch_bytes(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
) -> bytes:
    """The raw body, for binary feeds (protocol buffers)."""
    content, _ = await _get(url, headers=headers, params=params)
    return content


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
        key = url_key(link)
        if key in seen:
            continue
        seen.add(key)
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
