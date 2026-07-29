"""One-tap AI article summaries.

Tapping a headline opens a short model-written summary of the article with
the source link underneath. The article body is fetched through the guarded
news fetcher (SSRF-checked, size-capped), reduced to readable text, and
summarized by the Anthropic API. Summaries cache in Redis per (url, lang)
for a week — the model runs once per article per language, not per reader —
and a global daily cap brakes the spend regardless of traffic.
"""

import asyncio
import hashlib
import json
import re
from collections.abc import AsyncGenerator, AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal
from urllib.parse import urlsplit

import httpx
import structlog
from bs4 import BeautifulSoup, Tag

from outception.config import settings
from outception.exceptions import OutceptionError
from outception.link_preview.extractor import is_fetchable_async
from outception.redis import Redis
from outception.worker import enqueue_job

from . import cache as news_cache
from . import free_llm, gemini, gnews, translate
from .fetch import _MAX_BYTES, NewsFetchError, UnsafeURLError, fetch_html

log = structlog.get_logger()

_CACHE_KEY = "news:summary:{digest}"
_CACHE_TTL_SECONDS = 7 * 24 * 60 * 60
# A failing article (paywall, bot wall, too little text) must not be retried
# on every tap — fail fast from the marker for a couple of minutes.
_FAIL_KEY = "news:summary:fail:{digest}"
_FAIL_TTL_SECONDS = 120
# Definitive failures (the page is not an article, the Google News link can't
# be resolved, the publisher blocks even the reader) don't heal in minutes —
# remember them for a day so the tap goes straight to the article.
# "too short" is deliberately NOT here: a slow or JS-heavy page that served
# only a stub this once heals on the next fetch, and blacking the article out
# for a day cost readers summaries the very next attempt would have produced.
_DEAD_TTL_SECONDS = 24 * 60 * 60
_DEFINITIVE_FAILURES = (
    "not the article",
    "could not be resolved",
    "unsafe",
    "reader fallback failed: Client error",
)
# A publisher that keeps shutting our fetcher out is treated as unavailable as
# a whole for a while: readers tapping its other headlines get the article at
# once instead of watching a fetch that will fail the same way. One success
# clears it. Only failures that speak for the publisher count — a bot wall, a
# consent or paywall page, the reader refused as well. A page that is simply
# not an article (a video, a live page) says nothing about its neighbours, so
# it is remembered for itself and never held against the host.
_HOST_FAILURES = (
    "HTTP 401",
    "HTTP 403",
    "not the article",
    "reader fallback failed: Client error",
)
_HOST_FAIL_KEY = "news:summary:hostfail:{host}"
# One failing article may be re-tapped forever without speaking for its host:
# only distinct URLs count towards the limit (see _mark_failed).
_HOST_FAIL_SEEN_KEY = "news:summary:hostfail:seen:{host}:{url_hash}"
_HOST_FAIL_TTL_SECONDS = 6 * 60 * 60
_HOST_FAIL_LIMIT = 3
_DAILY_KEY = "news:summary:daily:{day}"
# Paid (Anthropic) summaries per day — the free Gemini tier is uncapped here.
_PAID_DAILY_KEY = "news:summary:paid:{day}"
# Single-flight: taps on the same (url, lang) while one is generating wait for
# its cache write instead of each paying for a model call of their own.
_PENDING_KEY = "news:summary:pending:{digest}"
_PENDING_TTL_SECONDS = 30
_PENDING_POLL_SECONDS = 0.25
# The panel gives up on an empty stream after ten seconds, and a reader who
# has watched it that long has already lost. A live tap gets this long to have
# the article in hand and this much more for the model to start writing;
# past either, the reader is sent to the article at once and the summary is
# finished by the background warmer, so the next tap finds it cached.
_LIVE_ARTICLE_SECONDS = 6.0
# Time-to-first-token on a 12k-char prompt regularly exceeds 3s on the free
# tier, and this deadline fired on 7 of every 12 live taps — each one bounced
# the reader out of a summary the model was about to write. The panel now
# waits (clients show it working for 10s), so spend that budget here rather
# than handing off a summary that was seconds from arriving.
_LIVE_FIRST_CHUNK_SECONDS = 6.0
# Whole-generation bound for the non-streaming (app) path, which has no
# first-token signal to work with. 6s fetch + this stays inside a reader's
# patience; anything slower is finished by the warmer instead.
_LIVE_MODEL_SECONDS = 8.0
# How long a duplicate tap waits on the leader's single-flight generation.
# Long enough to outlast what it is waiting for: a cold summary costs ~9s end
# to end, and the old 8s budget gave up about a second before the very result
# it was waiting for landed. It must clear the leader's OWN ceiling too — both
# live deadlines plus the scrub and cache write after them — or a waiter times
# out in the same breath as the result arrives. Derived, not a written number,
# so raising either deadline can't silently reintroduce that race. Stays under
# _PENDING_TTL_SECONDS, which must outlive the wait for the marker to mean
# anything.
_PENDING_WAIT_SECONDS = _LIVE_ARTICLE_SECONDS + _LIVE_MODEL_SECONDS + 2.0
# A deadline miss is remembered like any other fresh failure — a re-tap must
# not start the same slow fetch over — but with a value the warmer knows to
# ignore, or the handoff would be skipped as a known failure.
_FAIL_HANDOFF = "handoff"

_ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
_GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)
_MAX_ARTICLE_CHARS = 12_000
# Free hosted fetcher with a real browser: gets past bot walls and JS
# challenges that 403 our plain client (rte.ie, independent.ie, …).
_READER_URL = "https://r.jina.ai/"
_READER_TIMEOUT_SECONDS = 20.0
_MIN_ARTICLE_CHARS = 350
# When the article itself is out of reach (paywall, bot wall), the publisher's
# own standfirst — from the feed, or the page's description tag — is shown
# instead, labelled as theirs. Cached per (url, lang) for a day.
_TEASER_CACHE_KEY = "news:summary:teaser:{digest}"
_TEASER_CACHE_TTL_SECONDS = 24 * 60 * 60
_TEASER_MIN_CHARS = 40
_TEASER_MAX_CHARS = 400
# Pages that are never the article: YouTube pages are a player, not text.
# (Google News links are resolved to the publisher first — see gnews.py.)
_UNSUMMARIZABLE_HOSTS = frozenset(
    {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}
)

_client = httpx.AsyncClient(timeout=30.0)


class SummariesNotConfigured(OutceptionError):
    def __init__(self) -> None:
        super().__init__("Summaries are not configured", 503)


class SummaryUnavailable(OutceptionError):
    expected = True

    def __init__(self) -> None:
        super().__init__("Summary is unavailable for this article", 502)


class NoArticleText(NewsFetchError):
    """The page did not yield an article, but may have exposed a short
    publisher-written teaser (description tag, paywall standfirst)."""

    def __init__(self, reason: str, teaser: str | None = None) -> None:
        super().__init__(reason)
        self.teaser = teaser


class LiveDeadlinePassed(NewsFetchError):
    """A live tap ran out of time before the model started writing."""


SummaryKind = Literal["summary", "teaser"]


@dataclass(frozen=True)
class SummaryResult:
    text: str
    kind: SummaryKind


# Error pages and bot walls leak into feed descriptions and meta tags when a
# publisher's own pipeline hiccups — CoinDesk's feed served "Warning: Target
# URL returned error 429: Too Many Requests" as a description, and the card
# presented it as "the publisher's own summary". Shapes of machine noise only;
# topical words like "forbidden" stay allowed (a standfirst may legitimately
# contain them).
_TEASER_JUNK = re.compile(
    r"(?i)(?:^\s*warning:|(?:error|http|status)\s*\d{3}"
    # "Too many requests" is the one phrase here that also occurs in ordinary
    # prose ("the council received too many requests to process"), so it
    # counts as junk only next to a status code or an error/blocked word —
    # which is how a machine writes it, and how CoinDesk's leaked description
    # ("...returned error 429: Too Many Requests") reads.
    r"|(?:\b\d{3}\b|error|blocked|denied)[^.]{0,24}?too many requests"
    r"|too many requests[^.]{0,24}?(?:\b\d{3}\b|error|blocked|denied)"
    r"|access denied|enable (?:javascript|cookies)|are you a robot"
    r"|attention required|request blocked|verify you are human|captcha)"
)


def _clean_teaser(text: str | None) -> str | None:
    if not text:
        return None
    text = " ".join(text.split())
    if len(text) < _TEASER_MIN_CHARS:
        return None
    if _TEASER_JUNK.search(text):
        return None
    if len(text) > _TEASER_MAX_CHARS:
        cut = text.rfind(" ", 0, _TEASER_MAX_CHARS)
        text = text[: cut if cut > _TEASER_MIN_CHARS else _TEASER_MAX_CHARS] + "…"
    return text


def _meta_description(soup: BeautifulSoup) -> str | None:
    for tag in soup.find_all("meta"):
        if not isinstance(tag, Tag):
            continue
        if tag.get("property") != "og:description" and tag.get("name") != "description":
            continue
        content = tag.get("content")
        if isinstance(content, str):
            cleaned = _clean_teaser(content)
            if cleaned:
                return cleaned
    return None


def _is_unsummarizable(url: str) -> bool:
    try:
        host = urlsplit(url).hostname or ""
    except ValueError:
        return True
    return host in _UNSUMMARIZABLE_HOSTS


def _digest(url: str, lang: str) -> str:
    return hashlib.sha256(f"{url}|{lang}".encode()).hexdigest()[:32]


def _host(url: str) -> str:
    try:
        return urlsplit(url).hostname or ""
    except ValueError:
        return ""


def _is_definitive(exc: BaseException) -> bool:
    if isinstance(exc, UnsafeURLError):
        return True
    reason = str(exc)
    if not isinstance(exc, NewsFetchError) or "429" in reason:
        return False
    return any(marker in reason for marker in _DEFINITIVE_FAILURES)


def _is_host_failure(exc: BaseException) -> bool:
    reason = str(exc)
    if not isinstance(exc, NewsFetchError) or "429" in reason:
        return False
    return any(marker in reason for marker in _HOST_FAILURES)


async def _daily_used(redis: Redis) -> int:
    return int(
        await redis.get(_DAILY_KEY.format(day=datetime.now(UTC).strftime("%Y%m%d")))
        or 0
    )


async def _charge_daily(redis: Redis) -> None:
    """Spend one unit of the day's summary budget, with the article text already
    in hand and a model call about to go out. Charging any earlier let pages
    that never reach a model — paywalls, bot walls, dead links — burn the
    budget every reader shares, until taps redirected wall-wide."""
    day_key = _DAILY_KEY.format(day=datetime.now(UTC).strftime("%Y%m%d"))
    if await redis.incr(day_key) == 1:
        await redis.expire(day_key, 2 * 24 * 60 * 60)


async def _host_blocked(redis: Redis, url: str) -> bool:
    host = _host(url)
    if not host or gnews.is_google_news_url(url):
        return False
    failures = await redis.get(_HOST_FAIL_KEY.format(host=host))
    return int(failures or 0) >= _HOST_FAIL_LIMIT


async def _mark_failed(redis: Redis, url: str, digest: str, exc: BaseException) -> None:
    if isinstance(exc, LiveDeadlinePassed):
        await redis.set(
            _FAIL_KEY.format(digest=digest), _FAIL_HANDOFF, ex=_FAIL_TTL_SECONDS
        )
        return
    if not _is_definitive(exc):
        await redis.set(_FAIL_KEY.format(digest=digest), "1", ex=_FAIL_TTL_SECONDS)
        return
    await redis.set(_FAIL_KEY.format(digest=digest), "1", ex=_DEAD_TTL_SECONDS)
    host = _host(url)
    if host and _is_host_failure(exc) and not gnews.is_google_news_url(url):
        # Count each article once: re-tapping one failing URL must not reach
        # the limit — that let three taps on a single video page black out a
        # whole publisher's summaries for six hours.
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:32]
        seen_key = _HOST_FAIL_SEEN_KEY.format(host=host, url_hash=url_hash)
        if not await redis.set(seen_key, "1", ex=_HOST_FAIL_TTL_SECONDS, nx=True):
            return
        key = _HOST_FAIL_KEY.format(host=host)
        failures = await redis.incr(key)
        if failures == 1:
            await redis.expire(key, _HOST_FAIL_TTL_SECONDS)
        if failures == _HOST_FAIL_LIMIT:
            log.info("news.summary_host_blocked", host=host)


async def _mark_succeeded(redis: Redis, url: str, digest: str, summary: str) -> None:
    await redis.set(_CACHE_KEY.format(digest=digest), summary, ex=_CACHE_TTL_SECONDS)
    host = _host(url)
    if host:
        await redis.delete(_HOST_FAIL_KEY.format(host=host))


def extract_article_text(soup: BeautifulSoup) -> str:
    """Reduce a page to its readable article text: strip chrome elements,
    prefer the <article>/<main> container, fall back to all paragraphs."""
    for tag in soup(["script", "style", "nav", "aside", "footer", "header", "form"]):
        tag.decompose()
    container = soup.find("article") or soup.find("main") or soup
    parts = [p.get_text(" ", strip=True) for p in container.find_all("p")]
    text = "\n".join(part for part in parts if len(part) > 40)
    if len(text) < _MIN_ARTICLE_CHARS:
        # Paragraph-less layouts: fall back to the container's full text.
        text = container.get_text(" ", strip=True)
    return text[:_MAX_ARTICLE_CHARS]


def _system_prompt(lang: str) -> str:
    return (
        "You summarize news articles for a news reader app. Write 2 to 4"
        " short, punchy sentences covering the key facts, conversational"
        " and direct, like telling a sharp friend what happened, in plain"
        " everyday words. Stay accurate and grounded in the article: no"
        " hype, no opinions of your own. Never use quotation marks or"
        " dashes. No headline, no preamble, no bullet points, no"
        " markdown. If the text contains an article, summarize it even when"
        " a cookie notice, navigation text or a short teaser is mixed in."
        " Respond with exactly NO_ARTICLE only when there is no article"
        " content at all (just a consent wall, a paywall or subscription"
        " message, or an error page). Respond in"
        f" {translate.language_name(lang)} (ISO code '{lang}'), using only"
        " that language's standard script: never mix scripts or slip a"
        " character from another writing system into a word."
    )


# The model is told to avoid these, but style rules leak — scrub so no
# summary ever ships with quotes or dashes.
_SCRUB = {"—": ",", "–": ",", "--": ",", "“": "", "”": "", '"': ""}


def _scrub_piece(text: str) -> str:
    """_scrub_style for one streamed piece: the same character swaps, but no
    trimming — the whitespace at a chunk boundary is part of the prose."""
    for old, new in _SCRUB.items():
        text = text.replace(old, new)
    return text


def _scrub_style(text: str) -> str:
    for bad, good in _SCRUB.items():
        text = text.replace(bad, good)
    return " ".join(text.split())


async def _summarize_gemini(text: str, lang: str, key: str) -> str:
    response = await _client.post(
        _GEMINI_URL.format(model=settings.GEMINI_SUMMARY_MODEL),
        headers={
            "x-goog-api-key": key,
            "content-type": "application/json",
        },
        json={
            "system_instruction": {"parts": [{"text": _system_prompt(lang)}]},
            "contents": [{"parts": [{"text": text}]}],
            "generationConfig": {"maxOutputTokens": 400},
        },
    )
    response.raise_for_status()
    data = response.json()
    candidates = data.get("candidates") or []
    parts = (candidates[0].get("content") or {}).get("parts", []) if candidates else []
    return "".join(part.get("text", "") for part in parts).strip()


async def _summarize_anthropic(text: str, lang: str) -> str:
    response = await _client.post(
        _ANTHROPIC_URL,
        headers={
            "x-api-key": settings.ANTHROPIC_API_KEY or "",
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": settings.SUMMARY_MODEL,
            "max_tokens": 400,
            "system": _system_prompt(lang),
            "messages": [{"role": "user", "content": text}],
        },
    )
    response.raise_for_status()
    data = response.json()
    return "".join(block.get("text", "") for block in data.get("content", [])).strip()


_GEMINI_STREAM_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}"
    ":streamGenerateContent?alt=sse"
)


async def _raise_for_stream_status(response: httpx.Response) -> None:
    """raise_for_status for a streaming response: the error body has to be
    read first, or httpx raises ResponseNotRead instead of the HTTP error."""
    if response.status_code >= 400:
        await response.aread()
        response.raise_for_status()


async def _stream_gemini(text: str, lang: str, key: str) -> AsyncIterator[str]:
    async with _client.stream(
        "POST",
        _GEMINI_STREAM_URL.format(model=settings.GEMINI_SUMMARY_MODEL),
        headers={
            "x-goog-api-key": key,
            "content-type": "application/json",
        },
        json={
            "system_instruction": {"parts": [{"text": _system_prompt(lang)}]},
            "contents": [{"parts": [{"text": text}]}],
            "generationConfig": {"maxOutputTokens": 400},
        },
    ) as response:
        await _raise_for_stream_status(response)
        async for line in response.aiter_lines():
            if not line.startswith("data: "):
                continue
            data = json.loads(line[6:])
            candidates = data.get("candidates") or []
            parts = (
                (candidates[0].get("content") or {}).get("parts", [])
                if candidates
                else []
            )
            chunk = "".join(part.get("text", "") for part in parts)
            if chunk:
                yield chunk


async def _stream_anthropic(text: str, lang: str) -> AsyncIterator[str]:
    async with _client.stream(
        "POST",
        _ANTHROPIC_URL,
        headers={
            "x-api-key": settings.ANTHROPIC_API_KEY or "",
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": settings.SUMMARY_MODEL,
            "max_tokens": 400,
            "stream": True,
            "system": _system_prompt(lang),
            "messages": [{"role": "user", "content": text}],
        },
    ) as response:
        await _raise_for_stream_status(response)
        async for line in response.aiter_lines():
            if not line.startswith("data: "):
                continue
            data = json.loads(line[6:])
            if data.get("type") == "content_block_delta":
                chunk = (data.get("delta") or {}).get("text", "")
                if chunk:
                    yield chunk


async def _summarize_stream(redis: Redis, text: str, lang: str) -> AsyncGenerator[str]:
    """Streaming twin of _summarize: same provider order, budgets and
    cooldowns; yields text as the model writes it. A paid stream is counted
    once it has produced anything."""
    slot = await gemini.acquire(redis, settings.GEMINI_RPM_CAP)
    if slot is not None:
        index, key = slot
        produced = False
        try:
            async for chunk in _stream_gemini(text, lang, key):
                produced = True
                yield chunk
            if produced:
                return
            raise ValueError("empty summary")
        except (
            httpx.HTTPError,
            httpx.StreamError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            if produced:
                raise
            seconds = await gemini.note_failure(redis, index, exc)
            if settings.ANTHROPIC_API_KEY is None and not free_llm.configured():
                raise
            log.info("news.summary_gemini_fallback", error=str(exc), cooldown=seconds)
    # Second FREE line before paid. Whole-result rather than streamed — the
    # extra plumbing buys nothing: the panel types out single-chunk results,
    # and a generation is a couple of seconds either way.
    endpoint = await free_llm.acquire(redis)
    if endpoint is not None:
        try:
            summary = await free_llm.generate(_system_prompt(lang), text, endpoint)
            if summary:
                yield summary
                return
            raise ValueError("empty summary")
        except (httpx.HTTPError, ValueError, json.JSONDecodeError) as exc:
            await free_llm.note_failure(redis, endpoint, exc)
            if settings.ANTHROPIC_API_KEY is None:
                raise
            log.info(
                "news.summary_free_llm_fallback", endpoint=endpoint.id, error=str(exc)
            )
    if settings.ANTHROPIC_API_KEY is None:
        raise ValueError("no summary provider available")
    day_key = _PAID_DAILY_KEY.format(day=datetime.now(UTC).strftime("%Y%m%d"))
    used = int(await redis.get(day_key) or 0)
    if used >= settings.SUMMARY_PAID_DAILY_CAP:
        if used == settings.SUMMARY_PAID_DAILY_CAP:
            log.warning("news.summary_paid_cap", used=used)
        raise ValueError("paid summary cap reached")
    counted = False
    async for chunk in _stream_anthropic(text, lang):
        if not counted:
            counted = True
            if await redis.incr(day_key) == 1:
                await redis.expire(day_key, 2 * 24 * 60 * 60)
        yield chunk


async def _summarize(redis: Redis, text: str, lang: str) -> str:
    """Free tier first, paid backup second: Gemini handles the normal load at
    no cost; when it's out of quota or failing, Anthropic picks up the request
    — within a small daily paid budget, so a Gemini outage can't run up the
    Anthropic bill (over budget, the article simply has no summary today)."""
    slot = await gemini.acquire(redis, settings.GEMINI_RPM_CAP)
    if slot is not None:
        index, key = slot
        try:
            summary = await _summarize_gemini(text, lang, key)
            if summary:
                return summary
            raise ValueError("empty summary")
        except (httpx.HTTPError, ValueError, json.JSONDecodeError) as exc:
            seconds = await gemini.note_failure(redis, index, exc)
            if settings.ANTHROPIC_API_KEY is None and not free_llm.configured():
                raise
            log.info("news.summary_gemini_fallback", error=str(exc), cooldown=seconds)
    # Second FREE line before the paid backup (see free_llm.py).
    endpoint = await free_llm.acquire(redis)
    if endpoint is not None:
        try:
            summary = await free_llm.generate(_system_prompt(lang), text, endpoint)
            if summary:
                return summary
            raise ValueError("empty summary")
        except (httpx.HTTPError, ValueError, json.JSONDecodeError) as exc:
            await free_llm.note_failure(redis, endpoint, exc)
            if settings.ANTHROPIC_API_KEY is None:
                raise
            log.info(
                "news.summary_free_llm_fallback", endpoint=endpoint.id, error=str(exc)
            )
    if settings.ANTHROPIC_API_KEY is None:
        raise ValueError("no summary provider available")
    day_key = _PAID_DAILY_KEY.format(day=datetime.now(UTC).strftime("%Y%m%d"))
    used = int(await redis.get(day_key) or 0)
    if used >= settings.SUMMARY_PAID_DAILY_CAP:
        if used == settings.SUMMARY_PAID_DAILY_CAP:
            log.warning("news.summary_paid_cap", used=used)
        raise ValueError("paid summary cap reached")
    summary = await _summarize_anthropic(text, lang)
    if await redis.incr(day_key) == 1:
        await redis.expire(day_key, 2 * 24 * 60 * 60)
    return summary


async def _reader_text(url: str) -> str:
    """The article's readable text via Jina Reader. Untrusted page content,
    like any fetched article — it only ever becomes model input. The guard
    runs again here even though `_article_text` re-raises guard refusals:
    this path forwards the URL to a third party with our API key attached,
    so it must not depend on a caller remembering to pre-vet."""
    if not await is_fetchable_async(url):
        raise UnsafeURLError(f"unsafe or unresolvable URL: {url}")
    headers = {"Accept": "text/plain", "X-Return-Format": "text"}
    if settings.JINA_API_KEY:
        headers["Authorization"] = f"Bearer {settings.JINA_API_KEY}"
    # Streamed with the same byte cap as fetch._get: the reader relays
    # whatever the page serves, so an unbounded read would buffer a
    # length-lying body wholesale before the char cap below could apply.
    async with _client.stream(
        "GET", _READER_URL + url, headers=headers, timeout=_READER_TIMEOUT_SECONDS
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
            # Unknown charset name — fall back to utf-8, like fetch_text.
            text = bytes(buffer).decode("utf-8", "replace")
    lines = text.splitlines()
    # Drop the reader's metadata preamble (Title:/URL Source:/Published Time:).
    body = [
        ln
        for ln in lines
        if not ln.startswith(
            ("Title:", "URL Source:", "Published Time:", "Markdown Content:")
        )
    ]
    return "\n".join(ln for ln in body if len(ln.strip()) > 40)[:_MAX_ARTICLE_CHARS]


async def _article_text(url: str) -> str:
    """Article text from our own fetch, or — when the publisher blocks us or
    serves only a teaser — from the reader fallback. URLs our SSRF guard
    refused never reach the fallback. When neither yields an article, the
    error carries whatever short publisher text the page did expose."""
    short: str | None = None
    try:
        soup = await fetch_html(url)
        # Tree walking a whole page is CPU-bound like the parse itself.
        text = await asyncio.to_thread(extract_article_text, soup)
        if len(text) >= _MIN_ARTICLE_CHARS:
            return text
        reason = "article text too short"
        short = _meta_description(soup) or _clean_teaser(text)
    except UnsafeURLError:
        raise
    except NewsFetchError as exc:
        reason = str(exc)
    if not settings.READER_FALLBACK_ENABLED:
        raise NoArticleText(reason, short)
    try:
        text = await _reader_text(url)
    except httpx.HTTPError as exc:
        raise NoArticleText(f"{reason}; reader fallback failed: {exc}", short) from exc
    if len(text) < _MIN_ARTICLE_CHARS:
        raise NoArticleText(
            f"{reason}; reader fallback too short", short or _clean_teaser(text)
        )
    log.info("news.summary_reader_fallback", url=url, reason=reason)
    return text


async def _resolved_article_text(redis: Redis, url: str) -> str:
    """Article text behind *url*, resolving Google News links first."""
    fetch_url = url
    if gnews.is_google_news_url(url):
        resolved = (
            await gnews.resolve(redis, url) if settings.GNEWS_RESOLVE_ENABLED else None
        )
        if not resolved:
            raise NewsFetchError("google news link could not be resolved")
        fetch_url = resolved
    return await _article_text(fetch_url)


async def _started_in_time(
    stream: AsyncGenerator[str], seconds: float
) -> AsyncIterator[str]:
    """*stream*, with a deadline on its first chunk only: a model that has
    started writing keeps the reader's attention, one that has not is given
    up on before the panel does."""
    try:
        try:
            first = await asyncio.wait_for(anext(stream), seconds)
        except StopAsyncIteration:
            return
        except TimeoutError as exc:
            raise LiveDeadlinePassed("model did not start writing in time") from exc
        yield first
        async for chunk in stream:
            yield chunk
    finally:
        await stream.aclose()


async def _produce(
    redis: Redis,
    url: str,
    lang: str,
    *,
    gemini_only: bool,
    gemini_key: str = "",
    free_endpoint: free_llm.Endpoint | None = None,
    live: bool = False,
) -> str:
    """Fetch the article and produce its scrubbed summary. Raises the
    NewsFetchError family on anything that should fail-mark the article.

    ``gemini_only`` + ``gemini_key`` run the generation on exactly one
    already-acquired Gemini slot (the warmer's mode); ``free_endpoint`` is
    its free_llm twin — the warmer stays free-tier-only either way, it just
    has two free tiers to be on.

    ``live`` puts the article fetch on the same deadline the streaming path
    has: a reader is watching, and their client gives up at ~10s — without
    the bound a slow publisher plus the reader fallback could hold the tap
    for 40s that nobody was still waiting for. The background warmer keeps
    the unbounded fetch (nobody is watching it)."""
    if live:
        try:
            text = await asyncio.wait_for(
                _resolved_article_text(redis, url), _LIVE_ARTICLE_SECONDS
            )
        except TimeoutError as exc:
            raise LiveDeadlinePassed("article not fetched in time") from exc
    else:
        text = await _resolved_article_text(redis, url)
    await _charge_daily(redis)

    async def generate_once() -> str:
        if free_endpoint is not None:
            return await free_llm.generate(_system_prompt(lang), text, free_endpoint)
        if gemini_only:
            return await _summarize_gemini(text, lang, gemini_key or "")
        return await _summarize(redis, text, lang)

    generate = generate_once()
    if live:
        # The article fetch is bounded above but the generation was not, so a
        # slow model could hold a reader-facing request for the client's full
        # 30s timeout (26-34s seen in prod) — long after the panel gave up at
        # ten. Bound it and hand off: the urgent warm queue finishes the same
        # summary with nobody waiting, so the next tap is a cache hit.
        try:
            summary = await asyncio.wait_for(generate, _LIVE_MODEL_SECONDS)
        except TimeoutError as exc:
            raise LiveDeadlinePassed("model did not finish in time") from exc
    else:
        summary = await generate
    if not summary:
        raise NewsFetchError("empty summary")
    # The model's refusal sentinel: the fetched page wasn't the article
    # (consent wall, paywall, error page). Fail-mark instead of caching a
    # meta-response about cookie notices for a week.
    if "NO_ARTICLE" in summary[:40]:
        raise NewsFetchError("fetched page is not the article")
    if translate.script_mismatch(summary, lang, text, strict_fused=True):
        # The model slipped a character from another script: one more try,
        # then treat it as a transient failure rather than show garbage.
        log.info("news.summary_script_mismatch", lang=lang)
        if live:
            # A reader is watching, and a second full generation costs more
            # than the time they have left. Fail transiently now; the warmer
            # (live=False) still gets its retry with nobody waiting.
            raise ValueError("mixed script in summary")
        summary = await generate_once()
        if not summary or translate.script_mismatch(
            summary, lang, text, strict_fused=True
        ):
            raise ValueError("mixed script in summary")
    return _scrub_style(summary)


async def has_cached(redis: Redis, url: str, lang: str) -> bool:
    """Whether a finished result (summary or publisher teaser) for this
    url+lang is already in Redis — serving it costs neither a fetch nor a
    model call, so the callers' guards may wave it through."""
    return await _cached_result(redis, _digest(url, lang)) is not None


async def get_summary(redis: Redis, url: str, lang: str) -> str:
    """The article's summary text, cache-first (see get_summary_result)."""
    return (await get_summary_result(redis, url, lang)).text


def _decoded(value: bytes | str | None) -> str | None:
    if value is None:
        return None
    return value.decode() if isinstance(value, bytes) else value


async def _teaser_result(
    redis: Redis, url: str, lang: str, digest: str, exc: BaseException | None
) -> SummaryResult | None:
    """The publisher's own standfirst in the reader's language, when we have
    one: the feed's description first, else what the page exposed. One line
    through the normal translation batch (free tier first); no summarizer."""
    # Feed teasers are stored raw (cache.remember_items) and exc.teaser comes
    # straight off a failing page — both must pass the junk filter before they
    # can be presented as the publisher's words.
    teaser = _clean_teaser(await news_cache.get_teaser(redis, url))
    if teaser is None and isinstance(exc, NoArticleText):
        teaser = _clean_teaser(exc.teaser)
    if not teaser:
        return None
    translated = (await translate.translate_texts(redis, [teaser], lang))[0]
    await redis.set(
        _TEASER_CACHE_KEY.format(digest=digest),
        translated,
        ex=_TEASER_CACHE_TTL_SECONDS,
    )
    log.info("news.summary_teaser", url=url)
    return SummaryResult(translated, "teaser")


async def get_summary_result(redis: Redis, url: str, lang: str) -> SummaryResult:
    """The article's summary, cache-first (one model call per url+lang) — or,
    when the article is out of reach, the publisher's own teaser."""
    if (
        settings.ANTHROPIC_API_KEY is None
        and not gemini.configured()
        and not free_llm.configured()
    ):
        raise SummariesNotConfigured()
    if not url.startswith(("http://", "https://")) or _is_unsummarizable(url):
        raise SummaryUnavailable()

    digest = _digest(url, lang)
    cached = await _cached_result(redis, digest)
    if cached is not None:
        return cached
    if await redis.get(_FAIL_KEY.format(digest=digest)) is not None or (
        await _host_blocked(redis, url)
    ):
        # Known not to summarize: no fetch, but the feed's standfirst still serves.
        result = await _teaser_result(redis, url, lang, digest, None)
        if result is None:
            raise SummaryUnavailable()
        return result

    pending_key = _PENDING_KEY.format(digest=digest)
    if not await redis.set(pending_key, "1", ex=_PENDING_TTL_SECONDS, nx=True):
        return await _await_pending(redis, digest)
    try:
        return await _generate(redis, url, lang, digest)
    finally:
        await redis.delete(pending_key)


# Events of the streaming summary, as plain dicts for the SSE endpoint:
#   {"text": ..., "kind": ...}  a whole result (cache, teaser)
#   {"delta": ...}              the next piece of a summary being written
#   {"done": True, "kind": ...} the stream finished (text is final)
#   {"error": "unavailable"}    nothing to show; open the article
_NO_ARTICLE_WINDOW = 40


async def stream_summary(
    redis: Redis, url: str, lang: str
) -> AsyncIterator[dict[str, object]]:
    """The summary as it is written, for the tap-to-read panel. Same rules as
    get_summary_result (cache, teasers, failure memory, single flight, caps);
    only a fresh generation actually streams."""
    if (
        settings.ANTHROPIC_API_KEY is None
        and not gemini.configured()
        and not free_llm.configured()
    ):
        raise SummariesNotConfigured()
    if not url.startswith(("http://", "https://")) or _is_unsummarizable(url):
        yield {"error": "unavailable"}
        return
    digest = _digest(url, lang)
    cached = await _cached_result(redis, digest)
    if cached is not None:
        yield {"text": cached.text, "kind": cached.kind}
        return
    if await redis.get(_FAIL_KEY.format(digest=digest)) is not None or (
        await _host_blocked(redis, url)
    ):
        result = await _teaser_result(redis, url, lang, digest, None)
        yield (
            {"text": result.text, "kind": result.kind}
            if result
            else {"error": "unavailable"}
        )
        return
    pending_key = _PENDING_KEY.format(digest=digest)
    if not await redis.set(pending_key, "1", ex=_PENDING_TTL_SECONDS, nx=True):
        try:
            result = await _await_pending(redis, digest)
        except SummaryUnavailable:
            yield {"error": "unavailable"}
            return
        yield {"text": result.text, "kind": result.kind}
        return
    try:
        async for event in _stream_generate(redis, url, lang, digest):
            yield event
    finally:
        await redis.delete(pending_key)


async def _stream_generate(
    redis: Redis, url: str, lang: str, digest: str
) -> AsyncIterator[dict[str, object]]:
    used = await _daily_used(redis)
    if used >= settings.SUMMARY_DAILY_CAP:
        log.warning("news.summary_daily_cap", used=used)
        result = await _teaser_result(redis, url, lang, digest, None)
        yield (
            {"text": result.text, "kind": result.kind}
            if result
            else {"error": "unavailable"}
        )
        return

    written: list[str] = []
    try:
        try:
            text = await asyncio.wait_for(
                _resolved_article_text(redis, url), _LIVE_ARTICLE_SECONDS
            )
        except TimeoutError as exc:
            raise LiveDeadlinePassed("article not fetched in time") from exc
        await _charge_daily(redis)
        # Hold back the first characters: the refusal sentinel must never be
        # shown, and the reader should see prose, not a half-word.
        held = ""
        async for chunk in _started_in_time(
            _summarize_stream(redis, text, lang), _LIVE_FIRST_CHUNK_SECONDS
        ):
            if held is not None:
                held += chunk
                if len(held) < _NO_ARTICLE_WINDOW:
                    continue
                if "NO_ARTICLE" in held:
                    raise NewsFetchError("fetched page is not the article")
                piece, held = _scrub_piece(held), None  # type: ignore[assignment]
            else:
                piece = _scrub_piece(chunk)
            written.append(piece)
            yield {"delta": piece}
        if held:
            if "NO_ARTICLE" in held:
                raise NewsFetchError("fetched page is not the article")
            piece = _scrub_piece(held)
            written.append(piece)
            yield {"delta": piece}
        summary = _scrub_style("".join(written))
        if not summary:
            raise NewsFetchError("empty summary")
        if translate.script_mismatch(summary, lang, text, strict_fused=True):
            raise ValueError("mixed script in summary")
    except (
        NewsFetchError,
        httpx.HTTPError,
        httpx.StreamError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        log.info("news.summary_failed", url=url, error=str(exc))
        await _mark_failed(redis, url, digest, exc)
        if isinstance(exc, LiveDeadlinePassed):
            await note_warm_candidate(redis, url, lang, urgent=True)
        if written:
            # Something was already on screen; end the stream rather than
            # swap in a teaser under the reader's eyes.
            yield {"error": "unavailable"}
            return
        result = await _teaser_result(redis, url, lang, digest, exc)
        yield (
            {"text": result.text, "kind": result.kind}
            if result
            else {"error": "unavailable"}
        )
        return
    await _mark_succeeded(redis, url, digest, summary)
    yield {"done": True, "kind": "summary"}


async def _cached_result(redis: Redis, digest: str) -> SummaryResult | None:
    summary, teaser = await redis.mget(
        [_CACHE_KEY.format(digest=digest), _TEASER_CACHE_KEY.format(digest=digest)]
    )
    cached = _decoded(summary)
    if cached is not None:
        return SummaryResult(cached, "summary")
    held = _decoded(teaser)
    if held is not None:
        if _TEASER_JUNK.search(held):
            # Poisoned before the junk filter existed (or translated junk):
            # drop it so the next tap rebuilds from a clean source.
            await redis.delete(_TEASER_CACHE_KEY.format(digest=digest))
            return None
        return SummaryResult(held, "teaser")
    return None


async def _await_pending(redis: Redis, digest: str) -> SummaryResult:
    """Wait for the in-flight generation of this digest to land in the cache.
    Gives up as soon as the marker is gone without a result (the producer
    failed) or after the wait budget."""
    deadline = asyncio.get_running_loop().time() + _PENDING_WAIT_SECONDS
    pending_key = _PENDING_KEY.format(digest=digest)
    while True:
        result = await _cached_result(redis, digest)
        if result is not None:
            return result
        if (
            await redis.get(pending_key) is None
            or asyncio.get_running_loop().time() > deadline
        ):
            raise SummaryUnavailable()
        await asyncio.sleep(_PENDING_POLL_SECONDS)


async def _generate(redis: Redis, url: str, lang: str, digest: str) -> SummaryResult:
    # Global cost brake: the budget is read here and spent in `_produce`, once
    # the article is in hand and a model call is really about to happen.
    used = await _daily_used(redis)
    if used >= settings.SUMMARY_DAILY_CAP:
        log.warning("news.summary_daily_cap", used=used)
        result = await _teaser_result(redis, url, lang, digest, None)
        if result is None:
            raise SummaryUnavailable()
        return result

    try:
        summary = await _produce(redis, url, lang, gemini_only=False, live=True)
    except (NewsFetchError, httpx.HTTPError, ValueError, json.JSONDecodeError) as exc:
        log.info("news.summary_failed", url=url, error=str(exc))
        await _mark_failed(redis, url, digest, exc)
        if isinstance(exc, LiveDeadlinePassed):
            # Hand the slow article to the background warmer: the reader is
            # already gone, but the NEXT tap should find it cached.
            await note_warm_candidate(redis, url, lang, urgent=True)
        result = await _teaser_result(redis, url, lang, digest, exc)
        if result is None:
            raise SummaryUnavailable() from exc
        return result

    await _mark_succeeded(redis, url, digest, summary)
    return SummaryResult(summary, "summary")


async def is_available(redis: Redis, url: str, lang: str) -> bool:
    """Whether a tap on this headline can expect a summary — decided from what
    is already known (cache, failure markers, budget), never by fetching or
    calling a model. False means the reader should be sent to the article at
    once instead of waiting on a generation that will come back empty; True is
    a prognosis, not a promise."""
    if (
        settings.ANTHROPIC_API_KEY is None
        and not gemini.configured()
        and not free_llm.configured()
    ):
        return False
    if not url.startswith(("http://", "https://")) or _is_unsummarizable(url):
        return False
    digest = _digest(url, lang)
    day = datetime.now(UTC).strftime("%Y%m%d")
    host = _host(url)
    # Every one of these is independent — the early exits below are shortcuts,
    # not data dependencies — so they are read in one round trip. This runs on
    # every headline tap, where it was seven sequential trips to Redis.
    keys = [
        _CACHE_KEY.format(digest=digest),
        _TEASER_CACHE_KEY.format(digest=digest),
        news_cache.teaser_key(url),
        _FAIL_KEY.format(digest=digest),
        _DAILY_KEY.format(day=day),
        _PAID_DAILY_KEY.format(day=day),
        # The summary allowlist (headlines the wall has served) rides in the
        # same round trip — a separate EXISTS in the endpoint made every tap
        # pay one more.
        news_cache.known_key(url),
    ]
    host_key = (
        _HOST_FAIL_KEY.format(host=host)
        if host and not gnews.is_google_news_url(url)
        else None
    )
    if host_key is not None:
        keys.append(host_key)
    values = await redis.mget(keys)
    (
        summary_cached,
        teaser_cached,
        feed_teaser,
        failed,
        daily_used,
        paid_used,
        known,
    ) = values[:7]
    host_failures = values[7] if host_key is not None else None

    if summary_cached is not None:
        return True
    if teaser_cached is not None:
        return True
    # Checked only once nothing is cached: the allowlist exists to stop a
    # caller aiming a FETCH at an arbitrary URL, and a result we already hold
    # costs nothing to serve. Known-markers outlive their headlines by less
    # than the summary cache does, so gating on it first told readers "no
    # summary" for articles sitting finished in Redis.
    if known is None:
        return False
    # The publisher's standfirst from the feed serves even when the article
    # itself is known not to — but only if it would survive the junk filter,
    # or the pre-check promises a teaser that _teaser_result then refuses.
    if feed_teaser is not None and _clean_teaser(_decoded(feed_teaser)) is not None:
        return True
    if failed is not None:
        return False
    if int(host_failures or 0) >= _HOST_FAIL_LIMIT:
        return False
    if gnews.is_google_news_url(url):
        if not settings.GNEWS_RESOLVE_ENABLED:
            return False
        if await gnews.cached_resolution(redis, url) == "":
            return False
    if int(daily_used or 0) >= settings.SUMMARY_DAILY_CAP:
        return False
    # A fresh summary needs a provider that can actually run right now: Gemini
    # while its free tier holds, else the paid backup while its daily budget
    # holds. When neither can (Gemini's quota spent for the day and the paid
    # cap reached), say so, so the reader opens the article at once instead of
    # watching a caret that ends in a redirect. A publisher teaser would have
    # answered True above, so there is nothing softer to fall back to here.
    gemini_ready = gemini.configured() and await gemini.available(redis)
    free_ready = free_llm.configured() and await free_llm.available(redis)
    paid_ready = (
        settings.ANTHROPIC_API_KEY is not None
        and int(paid_used or 0) < settings.SUMMARY_PAID_DAILY_CAP
    )
    return gemini_ready or free_ready or paid_ready


# ---- Hero-summary warming ---------------------------------------------------
#
# The first tap on an article generates its summary live, which reads as "slow"
# (worst on non-English cards: translation + summary both cold). Readers
# overwhelmingly tap the hero headline, so serving a card queues that one URL
# for background pre-summarization. Strictly free: the warmer only ever calls
# Gemini (never the paid Anthropic backup), has its own daily cap, and stands
# down once live taps have consumed half the global budget — warming can brown
# out, real taps can't.

_WARM_QUEUE_KEY = "news:summary:warm"
# Handoffs from live taps: a reader has already waited for THIS article and
# been sent to it without a summary, so it jumps the hero queue. As one member
# of a 500-strong set it was a random SPOP draw, and re-taps kept missing the
# cache for as long as it took the warmer to happen to pick it.
_WARM_URGENT_KEY = "news:summary:warm:urgent"
_WARM_QUEUE_TTL_SECONDS = 6 * 60 * 60
_WARM_QUEUE_MAX = 500
_WARM_URGENT_MAX = 200
_WARM_DAILY_KEY = "news:summary:warmday:{day}"


async def note_warm_candidate(
    redis: Redis, url: str, lang: str, *, urgent: bool = False
) -> None:
    """Queue a hero headline for pre-summarization. One cheap SADD on the
    serving path; all real checks happen in the warmer task.

    ``urgent`` queues a live tap's handoff instead: FIFO, drained first, and
    admitted regardless of the hero queue's size — a reader has already been
    turned away from this one article, and the whole point of the handoff is
    that their next tap finds it cached."""
    if not gemini.configured() and not free_llm.configured():
        return
    if not url.startswith(("http://", "https://")) or _is_unsummarizable(url):
        return
    payload = f"{lang}\t{url}"
    if urgent:
        pipe = redis.pipeline()
        pipe.lpush(_WARM_URGENT_KEY, payload)
        pipe.ltrim(_WARM_URGENT_KEY, 0, _WARM_URGENT_MAX - 1)
        pipe.expire(_WARM_URGENT_KEY, _WARM_QUEUE_TTL_SECONDS)
        await pipe.execute()
        # Kick the warmer NOW rather than leaving the handoff to the cron: a
        # reader was just sent to the article without a summary, and on the
        # cron alone their re-tap misses the cache for up to the full
        # interval. The run lock is non-blocking, so a kick while a run is
        # already draining simply no-ops — and the job queue is request-bound
        # (flushed by middleware), absent in bare scripts/tests: missing
        # manager just means the cron picks the handoff up as before.
        try:
            enqueue_job("news.warm_summaries")
        except RuntimeError:
            pass
        return
    if await redis.scard(_WARM_QUEUE_KEY) >= _WARM_QUEUE_MAX:
        return
    pipe = redis.pipeline()
    pipe.sadd(_WARM_QUEUE_KEY, payload)
    pipe.expire(_WARM_QUEUE_KEY, _WARM_QUEUE_TTL_SECONDS)
    await pipe.execute()


async def pop_warm_candidate(redis: Redis) -> tuple[str, str] | None:
    """Next (url, lang) from the warm queue, or None when it's drained.
    Live-tap handoffs come first, oldest first; hero candidates after."""
    raw = await redis.rpop(_WARM_URGENT_KEY)
    if raw is None:
        raw = await redis.spop(_WARM_QUEUE_KEY)
    if raw is None:
        return None
    entry = raw.decode() if isinstance(raw, bytes) else str(raw)
    lang, sep, url = entry.partition("\t")
    if not sep:
        return None
    return url, lang


async def warm_summary(redis: Redis, url: str, lang: str) -> str:
    """Generate + cache one queued summary, free tier only. Returns 'warmed',
    'skipped' (already handled / budget exhausted) or 'failed' (generation
    error — the task's circuit breaker counts these)."""
    gemini_usable = gemini.configured() and await gemini.available(redis)
    free_usable = free_llm.configured() and await free_llm.available(redis)
    if not gemini_usable and not free_usable:
        return "skipped"
    if translate.canonical_target(lang) is None:
        # Queue entries predating the endpoint's language gate (or a junk
        # entry from a flush-less deploy) must not spend the warm budget.
        return "skipped"
    digest = _digest(url, lang)
    if await redis.get(_CACHE_KEY.format(digest=digest)) is not None:
        return "skipped"
    failed = _decoded(await redis.get(_FAIL_KEY.format(digest=digest)))
    if failed is not None and failed != _FAIL_HANDOFF:
        return "skipped"
    # Deliberately NOT gated on _host_blocked, unlike the reader-facing paths:
    # a blackout keeps every live tap off the publisher, so nothing would ever
    # re-probe it and it could only time out rather than be disproved. The
    # warmer probes with nobody waiting, and one success clears it (see
    # _mark_succeeded).

    day = datetime.now(UTC).strftime("%Y%m%d")
    total_used, warm_used = (
        int(value or 0)
        for value in await redis.mget(
            [_DAILY_KEY.format(day=day), _WARM_DAILY_KEY.format(day=day)]
        )
    )
    # The global counter includes the warmer's own runs; only what readers
    # spent says whether the day is busy enough to leave them the budget.
    if total_used - warm_used > settings.SUMMARY_DAILY_CAP // 2:
        return "skipped"
    if warm_used >= settings.SUMMARY_WARM_DAILY_CAP:
        return "skipped"
    # Gemini first (best quality per request), the second free line when it
    # has no slot to give — either way the warmer never touches paid.
    slot = (
        await gemini.acquire(redis, settings.GEMINI_RPM_CAP) if gemini_usable else None
    )
    endpoint = await free_llm.acquire(redis) if slot is None else None
    if slot is None and endpoint is None:
        return "skipped"  # this minute's free calls belong to live readers
    # Charged only now that the run is really going ahead. `_produce` spends the
    # global budget too, so the brake stays honest about total model calls.
    warm_key = _WARM_DAILY_KEY.format(day=day)
    if await redis.incr(warm_key) == 1:
        await redis.expire(warm_key, 2 * 24 * 60 * 60)

    try:
        summary = await _produce(
            redis,
            url,
            lang,
            gemini_only=True,
            gemini_key=slot[1] if slot else "",
            free_endpoint=endpoint,
        )
    except (NewsFetchError, httpx.HTTPError, ValueError, json.JSONDecodeError) as exc:
        log.info("news.summary_warm_failed", url=url, error=str(exc))
        await _mark_failed(redis, url, digest, exc)
        return "failed"

    await _mark_succeeded(redis, url, digest, summary)
    return "warmed"
