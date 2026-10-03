"""The SSRF guard that sits under every fetch of a URL the server did not
mint itself: feed URLs, article URLs, logos, product links.

Kept as plain functions (no service, no database) so they can be tested in
isolation and called from the request path and the worker alike.
"""

import ipaddress
import re
import socket
from collections.abc import Sequence
from typing import Any
from urllib.parse import urljoin, urlparse

import anyio

# Match http(s) URLs in plain text. Conservative: only URLs that start with a
# scheme and `://`. Trailing punctuation is stripped so "see https://x.com."
# does not yield `https://x.com.`.
_URL_RE = re.compile(r"https?://[^\s<>]+", re.IGNORECASE)
_TRAILING_PUNCT = ".,;:!?)”’»'\""

# Cloud metadata endpoints, blocked by host string before DNS so a literal
# address in the URL cannot slip past the resolver check.
_METADATA_HOSTS = frozenset({"169.254.169.254", "metadata.google.internal"})


def extract_urls(text: str) -> list[str]:
    """Return the unique http(s) URLs in `text`, preserving first-seen order."""
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
    unfetchable before DNS: a non-http scheme, no host, or a metadata host."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return None
    if parsed.scheme not in ("http", "https"):
        return None
    if not parsed.hostname:
        return None
    host = parsed.hostname
    if host in _METADATA_HOSTS:
        return None
    return host


def _all_addresses_global(infos: Sequence[tuple[Any, ...]]) -> bool:
    """True only if every resolved address is globally routable. Rejects
    private, loopback, link-local, multicast and reserved ranges, and their
    IPv6 equivalents, in one `is_global` check."""
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
    """Reject anything that could be an SSRF target: non-http schemes, hosts
    that resolve to private, loopback or link-local ranges, and the cloud
    metadata addresses. Both address families are resolved so an IPv6-only
    internal host cannot slip past an IPv4-only lookup.

    Synchronous, for worker and non-async code. On the request path use
    `is_fetchable_async` so the DNS lookup does not block the loop.
    """
    host = _host_to_resolve(url)
    if host is None:
        return False
    try:
        infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror, UnicodeError:
        return False
    return _all_addresses_global(infos)


async def is_fetchable_async(url: str) -> bool:
    """Async twin of `is_fetchable`: resolves DNS off the event loop so a slow
    resolver cannot stall every concurrent request."""
    host = _host_to_resolve(url)
    if host is None:
        return False
    try:
        infos = await anyio.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    except OSError, UnicodeError:
        return False
    return _all_addresses_global(infos)


def sanitize_image_url(image: str | None, base_url: str) -> str | None:
    """Resolve a page-supplied image URL against the page and validate it
    with the same guard as the page fetch. Clients load the result directly,
    so an unvalidated value is a beaconing vector. Returns the safe absolute
    URL, or None."""
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
