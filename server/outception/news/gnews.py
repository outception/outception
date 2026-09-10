"""Resolve Google News article links to the publisher's URL.

Two thirds of the wall's headlines are ``news.google.com/rss/articles/<id>``
links, which only reach the publisher through JavaScript, so the server could
never fetch the article behind them for a summary. The id is base64: older
ids carry the publisher URL inline; current ids (``AU_yqL…`` payload) need
Google's unofficial ``batchexecute`` endpoint to decode. That endpoint is not a
documented API, so everything here is best-effort with a cached negative
result - a failure means "no summary for this link", never an error.
"""

import base64
import hashlib
import html
import json
import re
from bisect import bisect_right
from typing import Any
from urllib.parse import quote, urlsplit

import httpx
import structlog

from outception.redis import Redis

from .fetch import NewsFetchError, _vet_response

log = structlog.get_logger()

_HOSTS = frozenset({"news.google.com"})
_CACHE_KEY = "news:gnews:resolve:{digest}"
_CACHE_TTL_SECONDS = 7 * 24 * 60 * 60
_NEGATIVE_TTL_SECONDS = 60 * 60
# The RSS-style page with explicit locale params is the variant that honours
# the consent-bypass cookie; the bare /articles/ path redirects to the
# consent interstitial (no signature attributes) from EU egress.
_ARTICLE_URL = (
    "https://news.google.com/rss/articles/{article_id}?oc=5&hl=en-US&gl=US&ceid=US:en"
)
_BATCH_URL = "https://news.google.com/_/DotsSplashUi/data/batchexecute"
_client = httpx.AsyncClient(
    timeout=10.0,
    follow_redirects=True,
    headers={
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
        ),
        # Skips the EU consent interstitial that otherwise replaces the page.
        "Cookie": "SOCS=CAI",
        "Accept-Language": "en-US,en;q=0.9",
    },
    # The host is fixed and the article id regex-constrained, but redirects
    # were followed blind - the one fetch path without the SSRF guard's
    # peer/redirect vetting. Google won't bounce us to a private address;
    # this makes sure nothing else can either.
    event_hooks={"response": [_vet_response]},
)


def is_google_news_url(url: str) -> bool:
    try:
        return (urlsplit(url).hostname or "") in _HOSTS
    except ValueError:
        return False


def article_id(url: str) -> str | None:
    """The opaque id from ``/rss/articles/<id>``, ``/articles/<id>`` or
    ``/read/<id>`` - None for any other Google News page."""
    try:
        path = urlsplit(url).path
    except ValueError:
        return None
    m = re.search(r"/(?:rss/)?(?:articles|read)/([A-Za-z0-9_-]+)", path)
    return m.group(1) if m else None


def decode_inline(article_id: str) -> str | None:
    """Older ids embed the publisher URL directly in the base64 payload."""
    try:
        raw = base64.urlsafe_b64decode(article_id + "=" * (-len(article_id) % 4))
    except (ValueError, TypeError):
        return None
    if raw.startswith(b"\x08\x13\x22"):
        raw = raw[3:]
    if raw.endswith(b"\xd2\x01\x00"):
        raw = raw[:-3]
    if not raw:
        return None
    length = raw[0]
    body = raw[2 : length + 2] if length >= 0x80 else raw[1 : length + 1]
    if body.startswith(b"AU_yqL"):
        return None  # current format: needs batchexecute
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        return None
    return text if text.startswith(("http://", "https://")) else None


# The page is ~140 KB and the only things wanted from it are two opaque
# attributes on one element. Parsing it with BeautifulSoup cost ~88 ms of
# event loop per resolution - with every concurrent request stalled behind it -
# so the scan below works with `str.find` and stays linear in the page size:
# a regex over the whole page looked cheaper but backtracked quadratically on
# malformed markup, which is just as much of an event-loop stall.
# A real parser ignores markup inside scripts and comments; a scan over raw
# text does not, and a decoy pair there would send us to batchexecute with the
# wrong signature - which fails silently and negative-caches the link for an
# hour. Skip anything inside them.
_SIGNATURE_MARK = "data-n-a-sg"
# Attribute values may themselves contain ">", so the tag scan steps over
# quoted runs rather than stopping at the first one.
_TAG_REST = re.compile(r"(?:[^>\"']|\"[^\"]*\"|'[^']*')*?>", re.S)
_SIGNATURE_ATTR = re.compile(r"\bdata-n-a-sg\s*=\s*([\"'])(.*?)\1", re.S | re.I)
_TIMESTAMP_ATTR = re.compile(r"\bdata-n-a-ts\s*=\s*([\"'])(.*?)\1", re.S | re.I)
# The element carrying the signature is a few hundred bytes; anything that
# does not close within this is not it.
_MAX_TAG_LENGTH = 4096


def _inert_ranges(lower: str) -> list[tuple[int, int]]:
    """[start, end) spans of scripts and comments in a lower-cased page. An
    unclosed one runs to the end of the page, exactly as a browser would read
    it."""
    ranges: list[tuple[int, int]] = []
    pos = 0
    while True:
        script = lower.find("<script", pos)
        comment = lower.find("<!--", pos)
        if script < 0 and comment < 0:
            return ranges
        if comment < 0 or (0 <= script < comment):
            after = lower[script + 7 : script + 8]
            if after and after not in " \t\n\r\f/>":
                pos = script + 7
                continue
            closer = lower.find("</script>", script + 7)
            start, end = script, closer + 9
        else:
            closer = lower.find("-->", comment + 4)
            start, end = comment, closer + 3
        if closer < 0:
            ranges.append((start, len(lower)))
            return ranges
        ranges.append((start, end))
        pos = end


def _signed_attributes(page: str) -> tuple[str, str] | None:
    """The signature and timestamp Google requires to hand back the publisher
    URL. Both are read from the same element, so a page carrying several never
    pairs one element's signature with another's timestamp."""
    lower = page.lower()
    inert = _inert_ranges(lower)
    inert_starts = [start for start, _ in inert]
    pos = 0
    while (at := lower.find(_SIGNATURE_MARK, pos)) >= 0:
        pos = at + len(_SIGNATURE_MARK)
        span = bisect_right(inert_starts, at) - 1
        if span >= 0 and at < inert[span][1]:
            continue
        tag_start = page.rfind("<", max(0, at - _MAX_TAG_LENGTH), at)
        tag_end = _TAG_REST.match(page, at, at + _MAX_TAG_LENGTH)
        if tag_start < 0 or tag_end is None:
            continue
        tag = page[tag_start : tag_end.end()]
        signature = _SIGNATURE_ATTR.search(tag)
        timestamp = _TIMESTAMP_ATTR.search(tag)
        if signature is None or timestamp is None:
            continue
        return html.unescape(signature.group(2)), html.unescape(timestamp.group(2))
    return None


async def _decode_remote(article_id: str) -> str | None:
    """Current-format ids: read the page's signature + timestamp, then ask the
    batchexecute endpoint for the publisher URL."""
    page = await _client.get(_ARTICLE_URL.format(article_id=article_id))
    page.raise_for_status()
    signed = _signed_attributes(page.text)
    if signed is None:
        return None
    signature, timestamp = signed
    req = [
        "Fbv4je",
        '["garturlreq",[["X","X",["X","X"],null,null,1,1,"US:en",null,1,null,'
        'null,null,null,null,0,1],"X","X",1,[1,1,1],1,1,null,0,0,null,0],'
        f'"{article_id}",{timestamp},"{signature}"]',
    ]
    payload = "f.req=" + quote(json.dumps([[req]]))
    response = await _client.post(
        _BATCH_URL,
        content=payload,
        headers={"content-type": "application/x-www-form-urlencoded;charset=UTF-8"},
    )
    response.raise_for_status()
    return _extract_url(response.text)


def _extract_url(text: str) -> str | None:
    """The batchexecute reply is a ``)]}'`` guard plus length-prefixed JSON
    chunks; the publisher URL sits inside a JSON string in the first chunk."""
    for chunk in text.split("\n"):
        chunk = chunk.strip()
        if not chunk.startswith("[["):
            continue
        try:
            data: Any = json.loads(chunk)
        except ValueError:
            continue
        found = _find_url(data)
        if found:
            return found
    return None


def _find_url(node: Any) -> str | None:
    if isinstance(node, str):
        if node.startswith(("http://", "https://")) and "google.com" not in node:
            return node
        if node.startswith("["):
            try:
                return _find_url(json.loads(node))
            except ValueError:
                return None
        return None
    if isinstance(node, list):
        for item in node:
            found = _find_url(item)
            if found:
                return found
    return None


def _cache_key(aid: str) -> str:
    return _CACHE_KEY.format(digest=hashlib.sha1(aid.encode()).hexdigest()[:24])


async def cached_resolution(redis: Redis, url: str) -> str | None:
    """What the cache already knows about a Google News link without touching
    Google: the publisher URL, "" for a cached failure, None when unknown."""
    aid = article_id(url)
    if aid is None:
        return ""
    cached = await redis.get(_cache_key(aid))
    if cached is None:
        return None
    return cached.decode() if isinstance(cached, bytes) else cached


async def resolve(redis: Redis, url: str) -> str | None:
    """The publisher URL behind a Google News link, cached; None when it
    can't be resolved (cached negatively for an hour so taps don't hammer
    Google)."""
    aid = article_id(url)
    if aid is None:
        return None
    key = _cache_key(aid)
    cached = await redis.get(key)
    if cached is not None:
        cached = cached.decode() if isinstance(cached, bytes) else cached
        return cached or None
    resolved = decode_inline(aid)
    if resolved is None:
        try:
            resolved = await _decode_remote(aid)
        except (httpx.HTTPError, ValueError, NewsFetchError) as exc:
            # NewsFetchError covers the vet hook's guard refusals: a weird
            # Google redirect must resolve to "unresolvable" (negative-cached
            # below), not escape as an article failure that dead-marks the
            # headline for a week.
            log.info("news.gnews_resolve_failed", error=str(exc))
            resolved = None
    await redis.set(
        key,
        resolved or "",
        ex=_CACHE_TTL_SECONDS if resolved else _NEGATIVE_TTL_SECONDS,
    )
    return resolved
