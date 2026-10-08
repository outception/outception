"""Article text: the page reduced to what a model should read, the
publisher's own teaser when the article is out of reach, and the hosted
reader fallback for publishers that wall off a plain client."""

import asyncio
from urllib.parse import urlsplit

import httpx
import structlog
from bs4 import BeautifulSoup, Tag

from outception.config import settings
from outception.net.guard import is_fetchable_async
from outception.news.fetch import pinned_transport
from outception.redis import Redis

from .. import gnews
from ..fetch import _MAX_BYTES, NewsFetchError, UnsafeURLError, fetch_html
from .errors import NoArticleText
from .teaser import clean_teaser

log = structlog.get_logger()

MAX_ARTICLE_CHARS = 12_000
MIN_ARTICLE_CHARS = 350
# A hosted fetcher with a real browser: gets past bot walls and script
# challenges that refuse a plain client.
READER_URL = "https://r.jina.ai/"
READER_TIMEOUT_SECONDS = 20.0
# Pages that are never the article: video pages are a player, not text.
# (Aggregator links are resolved to the publisher first; see gnews.py.)
UNSUMMARIZABLE_HOSTS = frozenset(
    {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}
)

_client = httpx.AsyncClient(timeout=30.0, transport=pinned_transport(), trust_env=False)


def is_unsummarizable(url: str) -> bool:
    try:
        host = urlsplit(url).hostname or ""
    except ValueError:
        return True
    return host in UNSUMMARIZABLE_HOSTS


def meta_description(soup: BeautifulSoup) -> str | None:
    for tag in soup.find_all("meta"):
        if not isinstance(tag, Tag):
            continue
        if tag.get("property") != "og:description" and tag.get("name") != "description":
            continue
        content = tag.get("content")
        if isinstance(content, str):
            cleaned = clean_teaser(content)
            if cleaned:
                return cleaned
    return None


def extract_article_text(soup: BeautifulSoup) -> str:
    """Reduce a page to its readable article text: strip chrome elements,
    prefer the <article>/<main> container, fall back to all paragraphs."""
    for tag in soup(["script", "style", "nav", "aside", "footer", "header", "form"]):
        tag.decompose()
    container = soup.find("article") or soup.find("main") or soup
    parts = [p.get_text(" ", strip=True) for p in container.find_all("p")]
    text = "\n".join(part for part in parts if len(part) > 40)
    if len(text) < MIN_ARTICLE_CHARS:
        # Paragraph-less layouts: fall back to the container's full text.
        text = container.get_text(" ", strip=True)
    return text[:MAX_ARTICLE_CHARS]


async def reader_text(url: str) -> str:
    """The article's readable text via the hosted reader. Untrusted page
    content, like any fetched article: it only ever becomes model input.
    The guard runs again here even though `article_text` re-raises guard
    refusals: this path forwards the URL to a third party with our key
    attached, so it must not depend on a caller remembering to pre-vet."""
    if not await is_fetchable_async(url):
        raise UnsafeURLError(f"unsafe or unresolvable URL: {url}")
    headers = {"Accept": "text/plain", "X-Return-Format": "text"}
    if settings.JINA_API_KEY:
        headers["Authorization"] = f"Bearer {settings.JINA_API_KEY}"
    # Streamed with the same byte cap as the fetcher: the reader relays
    # whatever the page serves, so an unbounded read would buffer a
    # length-lying body wholesale before the char cap below could apply.
    async with _client.stream(
        "GET", READER_URL + url, headers=headers, timeout=READER_TIMEOUT_SECONDS
    ) as response:
        response.raise_for_status()
        buffer = bytearray()
        async for chunk in response.aiter_bytes():
            buffer.extend(chunk)
            if len(buffer) > _MAX_BYTES:
                raise NewsFetchError(f"reader body too large for {url}")
        try:
            text = bytes(buffer).decode(response.charset_encoding or "utf-8", "replace")
        except LookupError:
            text = bytes(buffer).decode("utf-8", "replace")
    lines = text.splitlines()
    # Drop the reader's metadata preamble.
    body = [
        ln
        for ln in lines
        if not ln.startswith(
            ("Title:", "URL Source:", "Published Time:", "Markdown Content:")
        )
    ]
    return "\n".join(ln for ln in body if len(ln.strip()) > 40)[:MAX_ARTICLE_CHARS]


async def article_text(url: str) -> str:
    """Article text from our own fetch, or, when the publisher blocks us or
    serves only a teaser, from the reader fallback. URLs the guard refused
    never reach the fallback. When neither yields an article, the error
    carries whatever short publisher text the page did expose."""
    short: str | None = None
    try:
        soup = await fetch_html(url)
        # Tree walking a whole page is CPU-bound like the parse itself.
        text = await asyncio.to_thread(extract_article_text, soup)
        if len(text) >= MIN_ARTICLE_CHARS:
            return text
        reason = "article text too short"
        short = meta_description(soup) or clean_teaser(text)
    except UnsafeURLError:
        raise
    except NewsFetchError as exc:
        reason = str(exc)
    if not settings.READER_FALLBACK_ENABLED:
        raise NoArticleText(reason, short)
    try:
        text = await reader_text(url)
    except httpx.HTTPError as exc:
        raise NoArticleText(f"{reason}; reader fallback failed: {exc}", short) from exc
    if len(text) < MIN_ARTICLE_CHARS:
        raise NoArticleText(
            f"{reason}; reader fallback too short", short or clean_teaser(text)
        )
    log.info("news.summary_reader_fallback", url=url, reason=reason)
    return text


async def resolved_article_text(redis: Redis, url: str) -> str:
    """Article text behind *url*, resolving aggregator links first."""
    fetch_url = url
    if gnews.is_google_news_url(url):
        resolved = (
            await gnews.resolve(redis, url) if settings.GNEWS_RESOLVE_ENABLED else None
        )
        if not resolved:
            raise NewsFetchError("google news link could not be resolved")
        fetch_url = resolved
    return await article_text(fetch_url)
