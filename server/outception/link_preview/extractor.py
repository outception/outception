"""URL extraction + OpenGraph parsing helpers.

Kept as plain free functions (no service, no DB) so they can be tested
in isolation and called from both the API path (extract URLs to enqueue
fetches) and the worker path (parse a fetched HTML body).
"""

import ipaddress
import re
import socket
from collections.abc import Sequence
from typing import Any
from urllib.parse import urljoin, urlparse

import anyio

# Match http(s) URLs in plain text. Conservative — only catches URLs that
# start with a scheme + `://`, which is what the existing `linkifySegments`
# autolinker in the frontend also matches. Trailing punctuation like
# `,`, `.`, `)`, etc. is stripped so "see https://x.com." doesn't yield
# `https://x.com.` as the URL.
_URL_RE = re.compile(r"https?://[^\s<>]+", re.IGNORECASE)
_TRAILING_PUNCT = ".,;:!?)”’»'\""


def extract_urls(text: str) -> list[str]:
    """Return the unique http(s) URLs in `text`, preserving first-seen
    order. Trailing punctuation is stripped because users routinely write
    `look at this: https://foo.com.`"""
    seen: set[str] = set()
    out: list[str] = []
    for match in _URL_RE.finditer(text):
        url = match.group(0).rstrip(_TRAILING_PUNCT)
        if not url or url in seen:
            continue
        seen.add(url)
        out.append(url)
    return out


def _host_to_resolve(url: str) -> str | None:
    """Return the hostname to resolve for `url`, or None if the URL is
    unfetchable before we even hit DNS — non-http scheme, no host, or a
    literal cloud-metadata host."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return None
    if parsed.scheme not in ("http", "https"):
        return None
    if not parsed.hostname:
        return None
    host = parsed.hostname
    # AWS / GCP / Azure metadata IPv4. Block by host string before DNS
    # too, since the URL could embed the literal IP.
    if host == "169.254.169.254" or host == "metadata.google.internal":
        return None
    return host


def _all_addresses_global(infos: Sequence[tuple[Any, ...]]) -> bool:
    """True only if every resolved address is globally routable. Rejects
    private / loopback / link-local / multicast / reserved ranges (and their
    IPv6 equivalents) — `is_global` covers them in one check."""
    if not infos:
        return False
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            return False
        if not ip.is_global:
            return False
    return True


def is_fetchable(url: str) -> bool:
    """Reject anything that could be an SSRF target — non-http schemes,
    bare hostnames that resolve to private / loopback / link-local ranges,
    and the AWS / GCP metadata IP. The DNS lookup happens up front so a
    DNS-rebinding attack would also have to win the race with the worker
    actually fetching (deferred to a later hardening pass; this v1 closes
    the simple cases).

    Synchronous — safe from worker / non-async code. On the async request
    path use `is_fetchable_async` so the DNS lookup doesn't block the loop.
    """
    host = _host_to_resolve(url)
    if host is None:
        return False
    try:
        # Resolve BOTH families (A + AAAA) so an IPv6-only internal host
        # can't slip past an IPv4-only lookup.
        infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    except (socket.gaierror, UnicodeError):
        return False
    return _all_addresses_global(infos)


async def is_fetchable_async(url: str) -> bool:
    """Async twin of `is_fetchable`. Resolves DNS off the event loop
    (`anyio.getaddrinfo`) so a slow/unresponsive resolver can't stall every
    concurrent request served by the worker."""
    host = _host_to_resolve(url)
    if host is None:
        return False
    try:
        infos = await anyio.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    except (OSError, UnicodeError):
        return False
    return _all_addresses_global(infos)


def sanitize_image_url(image: str | None, base_url: str) -> str | None:
    """Resolve and validate a page's `og:image` before we store it.

    The client loads this URL directly, so an unvalidated value from an
    attacker-controlled page is a beaconing / client-side-SSRF vector (e.g.
    `og:image` pointing at an internal host, the cloud metadata IP, or a
    non-http scheme). We:

    - resolve relative / scheme-relative URLs against the page URL, and
    - run the result through the same `is_fetchable` guard as the page fetch
      (http(s) only, public host, no private/loopback/metadata targets).

    Returns the safe absolute URL, or None if it can't be validated.
    """
    stripped = (image or "").strip()
    if not stripped:
        return None
    try:
        absolute = urljoin(base_url, stripped)
    except ValueError:
        return None
    if not is_fetchable(absolute):
        return None
    return absolute


# Match OpenGraph (and a small set of fallbacks) meta tags. We're
# specifically lenient about quoting (single vs double) and attribute
# order — both common in scraped HTML — but strict about scoping to a
# single tag at a time so we don't accidentally read across.
_META_RE = re.compile(
    r"<meta\b[^>]*?\b(?:property|name)\s*=\s*['\"]?([^'\"\s>]+)['\"]?"
    r"[^>]*?\bcontent\s*=\s*['\"]([^'\"]*)['\"]",
    re.IGNORECASE,
)
_META_RE_ALT = re.compile(
    r"<meta\b[^>]*?\bcontent\s*=\s*['\"]([^'\"]*)['\"]"
    r"[^>]*?\b(?:property|name)\s*=\s*['\"]?([^'\"\s>]+)['\"]?",
    re.IGNORECASE,
)
_TITLE_RE = re.compile(r"<title\b[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def parse_open_graph(html: str) -> dict[str, str]:
    """Pull OG meta tags out of an HTML body. Returns a dict with the
    canonical keys we care about: `title`, `description`, `image`,
    `site_name`. Falls back to `<title>` when there's no `og:title`.

    Regex over BeautifulSoup keeps the dependency surface small for a
    parser that only needs a handful of attribute pairs — but it does
    mean we silently miss any tag that breaks the assumed shape (e.g.
    multi-line attribute lists). Acceptable v1 trade-off.
    """
    found: dict[str, str] = {}
    # Walk both attribute orderings (`property` first or `content` first)
    # — some sites build their meta tags the wrong way round.
    for match in _META_RE.finditer(html):
        key, value = match.group(1).lower(), match.group(2)
        if key not in found:
            found[key] = value
    for match in _META_RE_ALT.finditer(html):
        value, key = match.group(1), match.group(2).lower()
        if key not in found:
            found[key] = value

    out: dict[str, str] = {}
    if "og:title" in found:
        out["title"] = found["og:title"]
    elif (m := _TITLE_RE.search(html)) is not None:
        out["title"] = m.group(1).strip()
    if "og:description" in found:
        out["description"] = found["og:description"]
    elif "description" in found:
        out["description"] = found["description"]
    if "og:image" in found:
        out["image"] = found["og:image"]
    if "og:site_name" in found:
        out["site_name"] = found["og:site_name"]
    return out
