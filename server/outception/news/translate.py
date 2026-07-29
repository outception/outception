"""Keyless machine translation for news headlines.

News comes from 250+ sources in many languages; a reader who picked a UI
language (or was geo-detected into one) wants the headlines in it too. We proxy
Google's keyless translate endpoint — the same one the google-translate client
libraries use — and cache each ``(target, text)`` in Redis, so any given
headline is translated at most once per language regardless of how many readers
see it.

Speed matters: a card's headlines are translated as a batch. Cache reads are a
single Redis round-trip (``mget``), and the cold misses are packed into as few
upstream calls as possible — Google preserves newline separators, so a whole
card's worth of headlines translates in one request instead of one-per-headline.
"""

import asyncio
import hashlib
from typing import Any

import httpx
import structlog

from outception.config import settings
from outception.redis import Redis

from .fetch import NewsFetchError, fetch_json

log = structlog.get_logger()

_URL = "https://translate.googleapis.com/translate_a/single"
_CACHE_KEY = "news:xlate:{target}:{digest}"
_TTL_SECONDS = 24 * 60 * 60
# Pack headlines into one upstream call up to this many characters of joined
# text, so the request URL stays well under limits; longer batches split into
# a few chunks translated concurrently.
_MAX_CHUNK_CHARS = 1400
# Bound concurrent outbound calls so a cold multi-chunk batch doesn't open too
# many connections at once.
_semaphore = asyncio.Semaphore(8)

# Some UI locales aren't distinct engine languages: map them to the engine's
# nearest supported code (pt-PT → Portuguese, Croatian → its mutually
# intelligible neighbour Serbian for LibreTranslate, which lacks a Croatian
# model).
_GOOGLE_OVERRIDE = {
    "pt-PT": "pt",
    "zh-Hans": "zh-CN",
    "zh-Hant": "zh-TW",
    "nb": "no",
}
# LibreTranslate's Argos index uses zh/zt for Chinese; pt-PT collapses to
# Portuguese.
_LIBRE_OVERRIDE = {
    "pt-PT": "pt",
    "zh-Hans": "zh",
    "zh-Hant": "zt",
}
# LibreTranslate has no model for these, so they only ever use the public
# (Google) endpoint.
_LIBRE_UNSUPPORTED = frozenset({"sr", "hr"})

# The locales the app actually ships (mirrors packages/i18n). Any other target
# is rejected before it can reach the upstream or mint a cache key: without
# this, an unauthenticated caller could stream junk target codes to force cold
# translations (upstream amplification) and fill Redis with distinct-key trash.
_SUPPORTED_TARGETS = frozenset(
    {
        "ar",
        "bg",
        "bn",
        "ca",
        "cs",
        "da",
        "de",
        "el",
        "en",
        "es",
        "et",
        "eu",
        "fa",
        "fi",
        "fr",
        "ga",
        "he",
        "hi",
        "hr",
        "hu",
        "id",
        "it",
        "ja",
        "ko",
        "lt",
        "lv",
        "ms",
        "nb",
        "nl",
        "pl",
        "pt",
        "pt-PT",
        "ro",
        "ru",
        "sk",
        "sl",
        "sq",
        "sr",
        "sv",
        "th",
        "tl",
        "tr",
        "uk",
        "ur",
        "vi",
        "zh-Hans",
        "zh-Hant",
    }
)

# A dedicated client for a self-hosted LibreTranslate: the URL is operator
# config (trusted), so it deliberately bypasses the news fetch SSRF guard,
# which would otherwise block the internal/private address.
_libre_client = httpx.AsyncClient(timeout=15.0)


def _google_code(locale: str) -> str:
    """Google's ``tl`` param wants a language, not a region (pt-PT → pt)."""
    return _GOOGLE_OVERRIDE.get(locale, locale.split("-")[0])


def _libre_code(locale: str) -> str:
    if locale in _LIBRE_OVERRIDE:
        return _LIBRE_OVERRIDE[locale]
    return locale.split("-")[0]


def _cache_key(target: str, text: str) -> str:
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:20]
    return _CACHE_KEY.format(target=target, digest=digest)


def _decode(value: object) -> str | None:
    if value is None:
        return None
    return value.decode("utf-8") if isinstance(value, bytes) else str(value)


async def _call(q: str, target: str) -> list[list[Any]] | None:
    """One upstream translate call; returns the raw ``data[0]`` segment list or
    None on failure."""
    params = {
        "client": "gtx",
        "sl": "auto",
        "tl": _google_code(target),
        "dt": "t",
        "q": q,
    }
    try:
        data = await fetch_json(_URL, params=params)
        return data[0] or []
    except (NewsFetchError, IndexError, TypeError) as exc:
        log.info("news.translate_failed", target=target, error=str(exc))
        return None


async def _translate_one(text: str, target: str) -> str | None:
    """Translate a single string; returns None on failure so callers can tell a
    genuine failure from a translation that legitimately equals the input (a
    brand, a proper-noun headline, or a string already in the target language)."""
    async with _semaphore:
        segments = await _call(text, target)
    if segments is None:
        return None
    joined = "".join(seg[0] for seg in segments if seg and seg[0])
    return joined or None


async def _translate_lines(lines: list[str], target: str) -> list[str | None]:
    """Translate a chunk of headlines in a single upstream call by joining them
    with newlines — Google keeps the separators, so the translated blob splits
    back to one line per headline. Falls back to per-line translation if the
    line count doesn't survive the round trip. Failed lines come back as None."""
    async with _semaphore:
        segments = await _call("\n".join(lines), target)
    if segments is not None:
        blob = "".join(seg[0] for seg in segments if seg and seg[0])
        parts = blob.split("\n")
        if len(parts) == len(lines):
            return [part or None for part in parts]
    # Separators didn't line up (or the call failed): translate each on its own.
    return list(await asyncio.gather(*(_translate_one(line, target) for line in lines)))


async def _libre_call(texts: list[str], target: str) -> list[str | None]:
    """Translate a batch through a self-hosted LibreTranslate (it accepts an
    array natively). Failed items come back as None so they aren't cached as if
    translated."""
    url = f"{settings.LIBRETRANSLATE_URL.rstrip('/')}/translate"  # type: ignore[union-attr]
    payload: dict[str, Any] = {
        "q": texts,
        "source": "auto",
        "target": _libre_code(target),
        "format": "text",
    }
    if settings.LIBRETRANSLATE_API_KEY:
        payload["api_key"] = settings.LIBRETRANSLATE_API_KEY
    try:
        async with _semaphore:
            response = await _libre_client.post(url, json=payload)
        response.raise_for_status()
        out = response.json().get("translatedText")
        if isinstance(out, list) and len(out) == len(texts):
            return [str(t) or None for t in out]
    except (httpx.HTTPError, ValueError) as exc:
        log.info("news.libretranslate_failed", target=target, error=str(exc))
    return [None] * len(texts)


async def _libre_batch(texts: list[str], target: str) -> list[str | None]:
    result: list[str | None] = []
    for i in range(0, len(texts), 100):
        result.extend(await _libre_call(texts[i : i + 100], target))
    return result


async def _public_batch(texts: list[str], target: str) -> list[str | None]:
    """Translate *texts* via the keyless public endpoint, packed into
    length-bounded chunks translated concurrently. Failed items are None."""
    chunks: list[list[str]] = []
    current: list[str] = []
    length = 0
    for text in texts:
        if current and length + len(text) > _MAX_CHUNK_CHARS:
            chunks.append(current)
            current, length = [], 0
        current.append(text)
        length += len(text) + 1
    if current:
        chunks.append(current)

    translated = await asyncio.gather(
        *(_translate_lines(chunk, target) for chunk in chunks)
    )
    result: list[str | None] = []
    for chunk in translated:
        result.extend(chunk)
    return result


async def _translate_batch(texts: list[str], target: str) -> list[str | None]:
    """Translate *texts* with the fast public endpoint, falling back to the
    self-hosted LibreTranslate for the items it genuinely couldn't translate
    (rate-limited/failed — signalled as None, not by string equality, so a
    correct translation that happens to equal the input is never re-sent).
    LibreTranslate has no Serbian or Croatian model, so those stay on the public
    endpoint. Items still untranslated after all fallbacks stay None."""
    result = await _public_batch(texts, target)

    if not settings.LIBRETRANSLATE_URL or target in _LIBRE_UNSUPPORTED:
        return result

    misses = [i for i, value in enumerate(result) if value is None]
    if misses:
        retry = await _libre_batch([texts[i] for i in misses], target)
        for j, i in enumerate(misses):
            result[i] = retry[j]
    return result


async def translate_texts(redis: Redis, texts: list[str], target: str) -> list[str]:
    """Translate *texts* into *target*, aligned to the input order. Cache-first:
    the whole set is read from Redis in one ``mget``, only the misses hit the
    upstream (batched), and each *successful* result is cached for a day. Items
    that failed every upstream fall back to the original text and are NOT cached,
    so a transient rate-limit doesn't pin an untranslated headline for 24h."""
    if not texts:
        return []

    # Reject unsupported targets up front: no upstream call, no cache key. This
    # bounds cache-key cardinality to the known locale set and defuses the
    # junk-target amplification vector on every path that translates (the public
    # /translate proxy and the ?lang= source/search/feed endpoints alike).
    if target not in _SUPPORTED_TARGETS:
        return list(texts)

    results: list[str] = list(texts)
    keys = [_cache_key(target, text) for text in texts]
    cached = await redis.mget(keys)

    misses = [i for i, value in enumerate(cached) if _decode(value) is None]
    for i, value in enumerate(cached):
        decoded = _decode(value)
        if decoded is not None:
            results[i] = decoded

    if misses:
        translated = await _translate_batch([texts[i] for i in misses], target)
        to_cache = [
            (keys[i], value)
            for idx, i in enumerate(misses)
            if (value := translated[idx]) is not None
        ]
        for idx, i in enumerate(misses):
            if translated[idx] is not None:
                results[i] = translated[idx]  # type: ignore[assignment]
        if to_cache:
            async with redis.pipeline(transaction=False) as pipe:
                for key, value in to_cache:
                    pipe.set(key, value, ex=_TTL_SECONDS)
                await pipe.execute()

    return results
