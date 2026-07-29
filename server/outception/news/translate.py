"""Machine translation for news headlines.

News comes from 250+ sources in many languages; a reader who picked a UI
language (or was geo-detected into one) wants the headlines in it too. A
language model translates them — Gemini's free tier first, the Anthropic API as
the paid backup, the same split as article summaries — and each
``(target, text)`` is cached in Redis, so any given headline is translated at
most once per language regardless of how many readers see it.

Speed and cost: a card's headlines travel as one batch. Cache reads are a single
Redis round-trip (``mget``), the cold misses are packed into a few model calls
(a JSON array of headlines in, the same-length array out), and a global daily
cap on paid model calls brakes the spend regardless of traffic.
"""

import asyncio
import hashlib
import json
import re
import time
from datetime import UTC, datetime, timedelta

import httpx
import structlog

from outception.config import settings
from outception.redis import Redis

from . import free_llm, gemini

log = structlog.get_logger()

_ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
_GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)
# Versioned: v1 predates the explicit-script prompt (Cyrillic inside Croatian
# headlines), v2 predates the Sonnet upgrade and language-variety hints (Serbian
# vocabulary inside Croatian); bumping the key discards the old entries.
_CACHE_KEY = "news:xlate:v3:{target}:{digest}"
# A week: deck sources repeat headlines across days, and a translation that
# is already right should not be bought again tomorrow.
_TTL_SECONDS = 7 * 24 * 60 * 60
# Paid (Anthropic) calls per day, split into two independent budgets so the
# background warmer can never starve readers: the reader budget covers live
# requests; the warmer budget is a small allowance that pre-fills the deck's
# translations when Gemini's free tier is spent.
# v2: counted on success only (the old keys were charged per attempt,
# including failures, and cannot be trusted for the day they were written).
_PAID_DAILY_KEY = "news:xlate:paid:v2:{budget}:{day}"
# The warmer's Gemini (free-tier) batches per day — see the config comment.
_WARMER_FREE_DAILY_KEY = "news:xlate:free:warmer:{day}"
# A reader asked for this language recently: the warmer keeps it warm. Without
# demand gating the warmer would translate the deck into every locale for
# readers who don't exist.
# Reader demand per language, in hourly buckets: the warmer ranks languages
# by how many card views asked for them over the last day, so a language with
# one reader a day never starves the one people are actually reading in.
DEMAND_KEY = "news:xlate:demand:{target}:{hour}"
DEMAND_TTL_SECONDS = 25 * 60 * 60
DEMAND_WINDOW_HOURS = 24
# A background batch already in flight for these exact texts — stops every
# poller of a popular card from firing a duplicate model call each minute.
_PENDING_KEY = "news:xlate:pending:{target}:{digest}"
_PENDING_TTL_SECONDS = 120
# A batch that failed outright (both tries) is left alone for a while: every
# poll re-buying the same failure would cost money and keep the card flapping.
_FAILED_KEY = "news:xlate:failed:{target}:{digest}"
_FAILED_TTL_SECONDS = 10 * 60
# A batch nobody could take (every key benched, a timeout, the paid cap) is
# not a bad batch: park it only long enough to outlast a short bench, so the
# card's next poll tries again instead of showing originals for ten minutes.
_STARVED_TTL_SECONDS = 45
# Card requests wait this long for a fresh translation before serving the
# originals and letting the batch finish in the background — long enough for a
# normal model round-trip (~1 s), short enough that a stalled provider can
# never make a card feel broken.
_SOFT_WAIT_SECONDS = 1.5
# How often a poller waiting on someone else's in-flight batch re-reads the cache.
_CACHE_POLL_SECONDS = 0.25
# No reader waits on this (cards soft-wait then poll; the warmer runs in the
# background), so it only needs to be shorter than the pending claim. A third
# of 15-headline batches ran past 12 s in production and were thrown away.
_GEMINI_TIMEOUT_SECONDS = 25.0
# Headlines per model call: one feed's worth (feeds cap at 30 items), so the
# warmer spends exactly one call per source and language, and the output stays
# short enough for the token budget in every script.
# Smaller batches finish sooner and run in parallel, so a cold card lands
# inside the soft wait far more often (same cost — it is priced per token).
_MAX_BATCH = 15
_MAX_BATCH_CHARS = 4000
_MAX_OUTPUT_TOKENS = 2000
# Bound concurrent model calls so a cold multi-chunk batch doesn't fan out
# into too many connections at once.
_semaphore = asyncio.Semaphore(8)

_client = httpx.AsyncClient(timeout=30.0)

# The locales the app actually ships (mirrors packages/i18n), with the name the
# model is asked for. Any other target is rejected before it can reach the
# upstream or mint a cache key: without this, an unauthenticated caller could
# stream junk target codes to force cold translations (upstream amplification)
# and fill Redis with distinct-key trash.
_LANGUAGE_NAMES = {
    "ar": "Arabic",
    "bg": "Bulgarian",
    "bn": "Bengali",
    "ca": "Catalan (standard central Catalan)",
    "cs": "Czech",
    "da": "Danish",
    "de": "German",
    "el": "Greek",
    "en": "English",
    "es": "Spanish",
    "et": "Estonian",
    "eu": "Basque",
    "fa": "Persian",
    "fi": "Finnish",
    "fr": "French",
    "ga": "Irish",
    "he": "Hebrew",
    "hi": "Hindi",
    "hr": "Croatian (Latin script, standard Croatian vocabulary — never Serbian forms)",
    "hu": "Hungarian",
    "id": "Indonesian",
    "it": "Italian",
    "ja": "Japanese",
    "ko": "Korean",
    "lt": "Lithuanian",
    "lv": "Latvian",
    "ms": "Malay",
    "nb": "Norwegian Bokmål",
    "nl": "Dutch",
    "pl": "Polish",
    "pt": "Brazilian Portuguese",
    "pt-PT": "European Portuguese",
    "ro": "Romanian",
    "ru": "Russian",
    "sk": "Slovak",
    "sl": "Slovenian",
    "sq": "Albanian",
    "sr": "Serbian (Cyrillic script, ekavian, standard Serbian vocabulary)",
    "sv": "Swedish",
    "th": "Thai",
    "tl": "Filipino",
    "tr": "Turkish",
    "uk": "Ukrainian",
    "ur": "Urdu",
    "vi": "Vietnamese",
    "zh-Hans": "Simplified Chinese",
    "zh-Hant": "Traditional Chinese",
}
_SUPPORTED_TARGETS = frozenset(_LANGUAGE_NAMES)
_TARGETS_BY_LOWER = {target.lower(): target for target in _SUPPORTED_TARGETS}


def language_name(target: str) -> str:
    """The prompt-facing name (with script/variety hints) for a UI language."""
    return _LANGUAGE_NAMES.get(target, target)


def canonical_target(target: str) -> str | None:
    """The supported locale code for *target*, case-insensitive ('zh-hans' →
    'zh-Hans'); None when the language isn't one we serve. Every endpoint that
    keys a cache or a prompt on a caller-supplied language must go through
    this: an unvalidated code makes each request a guaranteed cache miss, so
    one caller minting codes can spend the day's model budget by itself."""
    return _TARGETS_BY_LOWER.get(target.lower())


# Character ranges of the scripts we serve. A translation or summary whose
# target is Latin-script but carries a CJK or Cyrillic character (the model
# slipped mid-word) is a failure, not a result — better the original than
# "I尔sko" on a Croatian card.
_SCRIPT_RANGES: dict[str, str] = {
    "cyrillic": "\u0400-\u04ff",
    "greek": "\u0370-\u03ff",
    "arabic": "\u0600-\u06ff\u0750-\u077f",
    "hebrew": "\u0590-\u05ff",
    "devanagari": "\u0900-\u097f",
    "bengali": "\u0980-\u09ff",
    "thai": "\u0e00-\u0e7f",
    "cjk": "\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af",
}
_TARGET_SCRIPT: dict[str, str] = {
    "ru": "cyrillic", "uk": "cyrillic", "bg": "cyrillic", "sr": "cyrillic",
    "el": "greek", "ar": "arabic", "fa": "arabic", "ur": "arabic", "he": "hebrew",
    "hi": "devanagari", "bn": "bengali", "th": "thai",
    "ja": "cjk", "ko": "cjk", "zh-Hans": "cjk", "zh-Hant": "cjk",
}  # fmt: skip
_FOREIGN_SCRIPT_RE: dict[str, re.Pattern[str]] = {}


def _echoed_source(item: str, source: str, target: str) -> bool:
    """The model returned the source text unchanged. For Latin-script targets
    `script_mismatch` can't see this (English looks fine), so an untranslated
    headline was being CACHED as the translation and pinned for the TTL. A
    long identical sentence is a miss; short titles (brand names, proper
    nouns) can legitimately be identical, so they pass."""
    if target == "en":
        return False
    if item.strip().casefold() != source.strip().casefold():
        return False
    return len(source.split()) >= 4


# Latin letters incl. the accented planes European languages actually use.
_LATIN_CHARS = "A-Za-zÀ-ɏ"
_FUSED_SCRIPT_RE: dict[str, re.Pattern[str]] = {}


def script_mismatch(
    text: str, target: str, source: str = "", *, strict_fused: bool = False
) -> bool:
    """True when *text* contains characters of a script that is not the
    target language's — unless the *source* text carried them too (a name
    written in its own script stays as it was). Latin letters are allowed
    everywhere.

    A foreign character FUSED directly into a word of the target's own script
    ("jasne政策 okvire" on a Croatian card) is the model slipping mid-word —
    but brand names genuinely fuse scripts ("小米SU7", "5μm"), so for
    translations the fusion is excused when the source headline carried those
    characters. Summaries pass ``strict_fused=True``: their "source" is a
    scraped page whose footer/nav junk carries stray foreign characters, which
    is exactly what excused the original slip."""
    own = _TARGET_SCRIPT.get(target, "latin")
    pattern = _FOREIGN_SCRIPT_RE.get(own)
    if pattern is None:
        ranges = "".join(r for name, r in _SCRIPT_RANGES.items() if name != own)
        pattern = re.compile(f"[{ranges}]")
        _FOREIGN_SCRIPT_RE[own] = pattern
    foreign = set(pattern.findall(text))
    if not foreign:
        return False
    excused = foreign <= set(pattern.findall(source))
    fused = _FUSED_SCRIPT_RE.get(own)
    if fused is None:
        own_chars = _SCRIPT_RANGES.get(own, _LATIN_CHARS)
        ranges = "".join(r for name, r in _SCRIPT_RANGES.items() if name != own)
        fused = re.compile(f"[{own_chars}][{ranges}]|[{ranges}][{own_chars}]")
        _FUSED_SCRIPT_RE[own] = fused
    if strict_fused or not excused:
        for match in fused.finditer(text):
            # Even under strict validation, a fused token copied VERBATIM from the
            # source is a preserved name or unit ("小米SU7", "5μm"), not a slip —
            # expand the hit to its whitespace-bounded token and look it up.
            start = match.start()
            end = match.end()
            while start > 0 and not text[start - 1].isspace():
                start -= 1
            while end < len(text) and not text[end].isspace():
                end += 1
            token = text[start:end].strip(".,;:!?()[]«»\"'。、，；：？！《》「」")
            if token and token in source:
                continue
            return True
    return not excused


# Typographic punctuation is the only non-ASCII an English headline normally
# carries; it must not send an English reader's own headlines to the model.
_TYPOGRAPHIC = str.maketrans("", "", "\u2018\u2019\u201c\u201d\u2013\u2014\u2026\u00a0")


def _needs_model(text: str, target: str) -> bool:
    """en→en is the identity for English headlines — no model call, no cache
    entry. Text that is non-ASCII beyond typographic punctuation may be a
    foreign headline an English reader wants translated, so it still goes to
    the model."""
    return not (target == "en" and text.translate(_TYPOGRAPHIC).isascii())


def _cache_key(target: str, text: str) -> str:
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:20]
    return _CACHE_KEY.format(target=target, digest=digest)


def _decode(value: object) -> str | None:
    if value is None:
        return None
    return value.decode("utf-8") if isinstance(value, bytes) else str(value)


def _system_prompt(target: str) -> str:
    return (
        "You translate news headlines for a news reader app. The user message"
        " is a numbered list of headlines, one per line. Reply with ONLY the"
        " same numbered list, one line per headline, same numbers and order,"
        " each line the headline translated"
        f" into {_LANGUAGE_NAMES[target]} (ISO code '{target}'). Keep names,"
        " numbers and brands; leave a headline unchanged if it is already in"
        " that language. Use only that language's standard script — never mix"
        " scripts within a headline. Write the simple, clear, natural headline"
        " a native news editor would — plain everyday words, never a stiff"
        " word-for-word rendering, with correct grammar and agreement."
        " Translate every ordinary word; only proper nouns, brand names and"
        " established loanwords stay untranslated. Use that language's own"
        " standard vocabulary — never forms borrowed from a neighbouring"
        " language. Keep any quotation marks as they are. No commentary, no"
        " markdown, no JSON."
    )


def _numbered(texts: list[str]) -> str:
    """Headlines as a numbered list: one line each, quotes untouched, no JSON
    escaping for the model to get wrong."""
    return "\n".join(f"{i}. {text}" for i, text in enumerate(texts, 1))


_NUMBERED_LINE = re.compile(r"^\s*(\d+)[.):]\s*(.*\S)\s*$")


def _parse(raw: str, count: int) -> list[str | None]:
    """The model's reply as one entry per input headline; raises ValueError
    when the shape doesn't match so the batch is treated as failed rather than
    misaligned. Numbered lines first (what we ask for); a JSON array is still
    accepted for models that insist."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.split("\n", 1)[1] if "\n" in text else ""
    numbered: dict[int, str] = {}
    for line in text.splitlines():
        match = _NUMBERED_LINE.match(line)
        if match:
            numbered.setdefault(int(match.group(1)), match.group(2).strip())
    if numbered and all(i in numbered for i in range(1, count + 1)):
        return [numbered[i] or None for i in range(1, count + 1)]
    # Tolerate a stray preamble or trailer around an array (an empty reply
    # still fails and the batch is retried on the next request).
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end <= start:
        raise ValueError("no numbered list or JSON array in translation reply")
    data = json.loads(text[start : end + 1])
    if not isinstance(data, list) or len(data) != count:
        raise ValueError("translation shape mismatch")
    return [item.strip() or None if isinstance(item, str) else None for item in data]


async def _generate_gemini(system: str, user: str, key: str) -> str:
    response = await _client.post(
        _GEMINI_URL.format(model=settings.GEMINI_TRANSLATION_MODEL),
        headers={
            "x-goog-api-key": key,
            "content-type": "application/json",
        },
        json={
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"parts": [{"text": user}]}],
            "generationConfig": {"maxOutputTokens": _MAX_OUTPUT_TOKENS},
        },
        timeout=_GEMINI_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    data = response.json()
    candidates = data.get("candidates") or []
    parts = (candidates[0].get("content") or {}).get("parts", []) if candidates else []
    return "".join(part.get("text", "") for part in parts).strip()


async def _generate_anthropic(system: str, user: str) -> str:
    response = await _client.post(
        _ANTHROPIC_URL,
        headers={
            "x-api-key": settings.ANTHROPIC_API_KEY or "",
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": settings.TRANSLATION_MODEL,
            "max_tokens": _MAX_OUTPUT_TOKENS,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        },
    )
    response.raise_for_status()
    data = response.json()
    return "".join(block.get("text", "") for block in data.get("content", [])).strip()


def _paid_cap(budget: str) -> int:
    if budget == "warmer":
        return settings.TRANSLATION_WARMER_PAID_DAILY_CAP
    return settings.TRANSLATION_PAID_DAILY_CAP


async def _count(redis: Redis, key: str) -> int:
    used = await redis.incr(key)
    if used == 1:
        await redis.expire(key, 2 * 24 * 60 * 60)
    return used


async def _acquire_gemini(redis: Redis, budget: str) -> tuple[int, str] | None:
    """A free-tier key + slot for this minute. The warmer can wait for the
    next minute (twice) when every key is only minute-full; a reader's batch
    must not, and goes paid instead. Neither waits when all keys are benched."""
    for attempt in range(3):
        slot = await gemini.acquire(redis, settings.GEMINI_RPM_CAP)
        if slot is not None:
            return slot
        if budget != "warmer" or attempt == 2 or not await gemini.available(redis):
            return None
        await asyncio.sleep(61 - datetime.now(UTC).second)
    return None


async def _generate(redis: Redis, system: str, user: str, budget: str) -> str:
    """Free tier first, paid backup second: Gemini handles the normal load at
    no cost; when it's out of quota or failing, Anthropic picks up the batch —
    against the caller's own daily paid budget ("reader" or "warmer"), so
    background warming can never starve live readers. Paid calls are counted
    when they succeed, so a provider error never eats the day's allowance."""
    started = time.monotonic()
    day = datetime.now(UTC).strftime("%Y%m%d")
    if gemini.configured():
        free_ok = True
        if budget == "warmer":
            # The warmer's share of the free tier; beyond it the rest of the
            # day's quota belongs to live readers and warming continues on
            # the warmer's own paid allowance instead. Read-only here and
            # counted on SUCCESS below (like the paid counter): charging per
            # attempt let a benching storm inflate the counter thousands past
            # the cap without one real translation, which then stood the
            # warmer down for the rest of the day on a fiction.
            used = int(await redis.get(_WARMER_FREE_DAILY_KEY.format(day=day)) or 0)
            if used >= settings.TRANSLATION_WARMER_FREE_DAILY_CAP:
                free_ok = False
        slot = await _acquire_gemini(redis, budget) if free_ok else None
        if slot is not None:
            index, key = slot
            try:
                text = await _generate_gemini(system, user, key)
                if text:
                    if budget == "warmer":
                        spent = await _count(
                            redis, _WARMER_FREE_DAILY_KEY.format(day=day)
                        )
                        if spent == settings.TRANSLATION_WARMER_FREE_DAILY_CAP:
                            log.info("news.translate_warmer_free_cap", used=spent)
                    log.info(
                        "news.translate_batch",
                        provider="gemini",
                        budget=budget,
                        ms=int((time.monotonic() - started) * 1000),
                    )
                    return text
                raise ValueError("empty translation")
            except (httpx.HTTPError, ValueError) as exc:
                seconds = await gemini.note_failure(redis, index, exc)
                if settings.ANTHROPIC_API_KEY is None:
                    raise NoTranslationCapacity(str(exc) or type(exc).__name__) from exc
                log.info(
                    "news.translate_gemini_fallback",
                    error=str(exc) or type(exc).__name__,
                    cooldown=seconds,
                )
        elif free_ok:
            log.info("news.translate_gemini_unavailable", budget=budget)
    # Second free line before any paid call: Groq/Mistral pick the batch up
    # when Gemini is benched, minute-full, or (for the warmer) share-spent.
    # Not gated on the warmer's Gemini share — that cap divides the GEMINI
    # fleet between warming and readers; these endpoints are bounded by their
    # own provider quotas and benching.
    endpoint = await free_llm.acquire(redis)
    if endpoint is not None:
        try:
            text = await free_llm.generate(system, user, endpoint)
            if text:
                log.info(
                    "news.translate_batch",
                    provider=endpoint.provider,
                    budget=budget,
                    ms=int((time.monotonic() - started) * 1000),
                )
                return text
            raise ValueError("empty translation")
        except (httpx.HTTPError, ValueError) as exc:
            await free_llm.note_failure(redis, endpoint, exc)
            if settings.ANTHROPIC_API_KEY is None:
                raise NoTranslationCapacity(str(exc) or type(exc).__name__) from exc
            log.info(
                "news.translate_free_llm_fallback",
                endpoint=endpoint.id,
                error=str(exc) or type(exc).__name__,
            )
    if settings.ANTHROPIC_API_KEY is None:
        raise NoTranslationCapacity("no translation provider available")
    paid_key = _PAID_DAILY_KEY.format(budget=budget, day=day)
    used = int(await redis.get(paid_key) or 0)
    if used >= _paid_cap(budget):
        # One warning per budget per day, not one per refused batch.
        if await redis.set(f"{paid_key}:warned", "1", ex=2 * 24 * 60 * 60, nx=True):
            log.warning("news.translate_paid_cap", budget=budget, used=used)
        raise NoTranslationCapacity("paid translation cap reached")
    text = await _generate_anthropic_with_retry(system, user)
    await _count(redis, paid_key)
    log.info(
        "news.translate_batch",
        provider="anthropic",
        budget=budget,
        ms=int((time.monotonic() - started) * 1000),
    )
    return text


async def _generate_anthropic_with_retry(system: str, user: str) -> str:
    """One retry after a short pause on the transient statuses Anthropic
    documents (rate limit, overloaded, gateway) — a burst must not turn into
    an untranslated card."""
    try:
        return await _generate_anthropic(system, user)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code not in (429, 500, 502, 503, 529):
            raise
    except httpx.TransportError:
        pass
    await asyncio.sleep(1.5)
    return await _generate_anthropic(system, user)


async def _generate_parsed(
    redis: Redis, texts: list[str], target: str, budget: str
) -> list[str | None]:
    """One model call, parsed; a malformed reply gets exactly one more try
    (models are stochastic) before the chunk counts as failed."""
    for attempt in range(2):
        raw = await _generate(redis, _system_prompt(target), _numbered(texts), budget)
        try:
            return _parse(raw, len(texts))
        except (ValueError, json.JSONDecodeError) as exc:
            if attempt == 1:
                raise ValueError(f"unparsable translation reply: {exc}") from exc
            log.info("news.translate_reply_retry", target=target, error=str(exc))
    raise ValueError("unreachable")


async def _translate_chunk(
    redis: Redis, texts: list[str], target: str, budget: str
) -> list[str | None]:
    """One model call for a chunk of headlines. Failed chunks come back as
    None per item so they aren't cached as if translated."""
    try:
        async with _semaphore:
            items = await _generate_parsed(redis, texts, target, budget)
        clean = [
            None
            if item is not None
            and (
                script_mismatch(item, target, source)
                or _echoed_source(item, source, target)
            )
            else item
            for item, source in zip(items, texts)
        ]
        # An echo can be the CORRECT translation (the prompt says to leave
        # proper-noun headlines and already-target-language text unchanged),
        # but treating every echo as a failure made those rejections
        # deterministic: never cached, re-bought on every poll in every
        # language, forever — the standing budget drain behind the frozen
        # part-English cards. Ask once more for just the echoed items: a
        # DIFFERENT reply wins, and a second identical echo is accepted as
        # the model insisting — either way the value caches and the loop ends.
        echoed = [
            i
            for i, (item, source) in enumerate(zip(items, texts))
            if item is not None
            and clean[i] is None
            and not script_mismatch(item, target, source)
        ]
        if echoed:
            # Isolated: a retry failure (unparsable, capacity) must not throw
            # away the good translations already in `clean` — that would
            # recreate the re-buy loop this block exists to end.
            try:
                retry_texts = [texts[i] for i in echoed]
                async with _semaphore:
                    retried = await _generate_parsed(redis, retry_texts, target, budget)
                for slot, item in zip(echoed, retried):
                    if item is None or script_mismatch(item, target, texts[slot]):
                        continue
                    if not _echoed_source(item, texts[slot], target):
                        clean[slot] = item
                    elif item.strip().casefold() == texts[slot].strip().casefold():
                        clean[slot] = texts[slot]
            except NoTranslationCapacity:
                if all(value is None for value in clean):
                    # Nothing salvaged from the first pass either: propagate
                    # so the batch parks on the short starved TTL, not the
                    # ten-minute failure park.
                    raise
                log.info("news.translate_echo_retry_starved", target=target)
            except (httpx.HTTPError, ValueError) as exc:
                log.info(
                    "news.translate_echo_retry_failed", target=target, error=str(exc)
                )
        if clean != items:
            log.info("news.translate_script_mismatch", target=target)
        return clean
    except NoTranslationCapacity as exc:
        log.info("news.translate_starved", target=target, error=str(exc))
        raise
    except (httpx.HTTPError, ValueError) as exc:
        log.info("news.translate_failed", target=target, error=str(exc))
        return [None] * len(texts)


def _chunks(texts: list[str]) -> list[list[str]]:
    chunks: list[list[str]] = []
    current: list[str] = []
    length = 0
    for text in texts:
        if current and (
            len(current) >= _MAX_BATCH or length + len(text) > _MAX_BATCH_CHARS
        ):
            chunks.append(current)
            current, length = [], 0
        current.append(text)
        length += len(text)
    if current:
        chunks.append(current)
    return chunks


def _demand_hours(now: datetime | None = None) -> list[str]:
    now = now or datetime.now(UTC)
    return [
        (now - timedelta(hours=offset)).strftime("%Y%m%d%H")
        for offset in range(DEMAND_WINDOW_HOURS)
    ]


async def note_demand(redis: Redis, target: str) -> None:
    """A reader asked for *target*: count it towards the warmer's ranking."""
    if target not in _SUPPORTED_TARGETS or target == "en":
        return
    key = DEMAND_KEY.format(target=target, hour=_demand_hours()[0])
    if await redis.incr(key) == 1:
        await redis.expire(key, DEMAND_TTL_SECONDS)


async def demanded_targets(redis: Redis) -> list[str]:
    """Languages readers asked for in the last day, most-requested first."""
    targets = sorted(t for t in _SUPPORTED_TARGETS if t != "en")
    hours = _demand_hours()
    keys = [DEMAND_KEY.format(target=t, hour=h) for t in targets for h in hours]
    values = await redis.mget(keys)
    ranked: list[tuple[int, str]] = []
    for i, target in enumerate(targets):
        window = values[i * len(hours) : (i + 1) * len(hours)]
        total = sum(int(v) for v in window if v is not None)
        if total > 0:
            ranked.append((total, target))
    ranked.sort(key=lambda pair: (-pair[0], pair[1]))
    return [target for _, target in ranked]


async def warmer_out_of_budget(redis: Redis) -> bool:
    """True when the warmer has spent both its free-tier share and its paid
    allowance for the day. A broke warmer MUST stand down entirely: its
    retries still seized the per-chunk single-flight claims and then failed,
    which locked live readers — whose own paid budget was still available —
    out of translating those very batches. That loop, not capacity itself,
    was what kept partially-translated cards frozen for whole days."""
    day = datetime.now(UTC).strftime("%Y%m%d")
    free_used, paid_spent = (
        int(value or 0)
        for value in await redis.mget(
            [
                _WARMER_FREE_DAILY_KEY.format(day=day),
                _PAID_DAILY_KEY.format(budget="warmer", day=day),
            ]
        )
    )
    if (
        free_used < settings.TRANSLATION_WARMER_FREE_DAILY_CAP
        or paid_spent < settings.TRANSLATION_WARMER_PAID_DAILY_CAP
    ):
        return False
    # Gemini share and paid allowance both spent — but the second free line
    # may still serve, so the warmer only stands down when that is out too.
    return not (free_llm.configured() and await free_llm.available(redis))


async def paid_used(redis: Redis, budget: str) -> int:
    """Paid batches *budget* has spent today."""
    key = _PAID_DAILY_KEY.format(
        budget=budget, day=datetime.now(UTC).strftime("%Y%m%d")
    )
    return int(await redis.get(key) or 0)


class NoTranslationCapacity(ValueError):
    """No provider could take the batch right now: Gemini benched or timing
    out with no paid backup, or the paid allowance for the day spent."""


async def cached_translations(redis: Redis, texts: list[str], target: str) -> list[str]:
    """Cache hits only — misses come back as the original text, and nothing
    reaches a model or writes a key. This is what the public /translate proxy
    serves: its texts are caller-supplied, and translating those cached each
    model reply under the genuine headline's hash, so one crafted batch could
    poison every reader's translation of a real headline for a week (and the
    same route drained the shared daily budget). First-party clients never
    call it — cards translate server-side — so cache-only costs nothing."""
    if not texts or target not in _SUPPORTED_TARGETS:
        return list(texts)
    results = list(texts)
    cached = await redis.mget([_cache_key(target, text) for text in texts])
    for i, value in enumerate(cached):
        decoded = _decode(value)
        if decoded is not None:
            results[i] = decoded
    return results


async def uncached_count(redis: Redis, texts: list[str], target: str) -> int:
    """How many of *texts* would need the model right now."""
    if not texts or target not in _SUPPORTED_TARGETS:
        return 0
    cached = await redis.mget([_cache_key(target, text) for text in texts])
    return sum(
        1
        for text, value in zip(texts, cached)
        if _decode(value) is None and _needs_model(text, target)
    )


_background_tasks: set[asyncio.Task[tuple[list[str | None], list[int]]]] = set()


async def _translate_and_store(
    redis: Redis, texts: list[str], keys: list[str], target: str, budget: str
) -> tuple[list[str | None], list[int], bool]:
    """Translate in chunks, caching each the moment it lands. Also returns the
    indices whose chunk was already in flight for another poller — those come
    back None here and appear in the cache when that poller's write lands —
    and whether any chunk went untranslated for want of capacity.

    Holding every chunk's write until the slowest one returned was what made a
    cold card wait: the reader's request gives up after `_SOFT_WAIT_SECONDS`
    and other pollers watch the cache every 250 ms, so a chunk that finished in
    under a second was invisible to both until its slow neighbour arrived."""
    chunks = _chunks(texts)
    offsets: list[int] = []
    start = 0
    for chunk in chunks:
        offsets.append(start)
        start += len(chunk)
    starved = False

    async def translate_and_cache(
        chunk: list[str], offset: int
    ) -> tuple[list[str | None], bool]:
        # Claimed per chunk, not per batch. Caching chunks as they land means a
        # poller arriving mid-flight computes a *smaller* miss list — so a
        # batch-level marker would let it start a second model call for the
        # chunk still in flight, on the busiest cards. This claim is the only
        # single-flight guard: a batch-level one keyed on the same texts would
        # collide with it whenever the batch is a single chunk.
        claim = _pending_key(target, chunk)
        if not await redis.set(claim, "1", ex=_PENDING_TTL_SECONDS, nx=True):
            return [None] * len(chunk), False
        try:
            values = await _translate_chunk(redis, chunk, target, budget)
        except NoTranslationCapacity:
            nonlocal starved
            starved = True
            values = [None] * len(chunk)
        finally:
            await redis.delete(claim)
        landed = [
            (keys[offset + index], value)
            for index, value in enumerate(values)
            if value is not None
        ]
        if landed:
            async with redis.pipeline(transaction=False) as pipe:
                for key, value in landed:
                    pipe.set(key, value, ex=_TTL_SECONDS)
                await pipe.execute()
        return values, True

    done = await asyncio.gather(
        *(
            translate_and_cache(chunk, offset)
            for chunk, offset in zip(chunks, offsets, strict=True)
        )
    )
    translated: list[str | None] = []
    lost: list[int] = []
    for (values, chunk_ran), offset in zip(done, offsets, strict=True):
        if not chunk_ran:
            lost.extend(range(offset, offset + len(values)))
        translated.extend(values)
    return translated, lost, starved


def _batch_digest(texts: list[str]) -> str:
    return hashlib.sha1("\n".join(texts).encode("utf-8")).hexdigest()[:20]


def _pending_key(target: str, texts: list[str]) -> str:
    return _PENDING_KEY.format(target=target, digest=_batch_digest(texts))


def _failed_key(target: str, texts: list[str]) -> str:
    return _FAILED_KEY.format(target=target, digest=_batch_digest(texts))


async def _wait_for_cache(
    redis: Redis, keys: list[str], deadline: float
) -> list[str | None]:
    """Poll the cache for another poller's in-flight batch until *deadline*
    (a monotonic timestamp); whatever has landed by then is returned."""
    while True:
        values = [_decode(v) for v in await redis.mget(keys)]
        remaining = deadline - time.monotonic()
        if all(v is not None for v in values) or remaining <= 0:
            return values
        await asyncio.sleep(min(_CACHE_POLL_SECONDS, remaining))


async def _start_background_translation(
    redis: Redis, texts: list[str], keys: list[str], target: str, budget: str
) -> "asyncio.Task[tuple[list[str | None], list[int]]]":
    """Kick off the miss translation for the card paths and hand back the task
    so the caller can soft-wait on it. Single flight is per chunk, inside
    `_translate_and_store`: chunks already in flight for another poller come
    back None (and listed), and the cache fills with that poller's result."""

    async def _run() -> tuple[list[str | None], list[int]]:
        # A batch that ran here and failed outright is parked (see
        # _FAILED_KEY); one whose chunks were merely claimed elsewhere is not —
        # parking it would stop the next poll from ever picking up the
        # translations the other poller is about to cache.
        result, lost, starved = await _translate_and_store(
            redis, texts, keys, target, budget
        )
        if len(lost) < len(result) and all(value is None for value in result):
            await redis.set(
                _failed_key(target, texts),
                "1",
                ex=_STARVED_TTL_SECONDS if starved else _FAILED_TTL_SECONDS,
            )
        return result, lost

    task = asyncio.create_task(_run())
    _background_tasks.add(task)

    def _done(t: "asyncio.Task[tuple[list[str | None], list[int]]]") -> None:
        _background_tasks.discard(t)
        if not t.cancelled() and t.exception() is not None:
            log.info("news.translate_background_failed", error=str(t.exception()))

    task.add_done_callback(_done)
    return task


async def translate_texts(
    redis: Redis,
    texts: list[str],
    target: str,
    *,
    budget: str = "reader",
    block: bool = True,
) -> list[str]:
    """See :func:`translate_texts_with_status`; this drops the pending flag."""
    results, _ = await translate_texts_with_status(
        redis, texts, target, budget=budget, block=block
    )
    return results


async def translate_texts_with_status(
    redis: Redis,
    texts: list[str],
    target: str,
    *,
    budget: str = "reader",
    block: bool = True,
) -> tuple[list[str], bool]:
    """Translate *texts* into *target*, aligned to the input order, plus
    whether any of them is still being translated (so a card can poll again
    soon instead of waiting a full refresh cycle). Cache-first:
    the whole set is read from Redis in one ``mget``, only the misses hit the
    model (batched), and each *successful* result is cached for a day. Items
    that failed upstream fall back to the original text and are NOT cached,
    so a transient failure doesn't pin an untranslated headline for 24h.

    ``budget`` names whose paid allowance a Gemini miss may spend ("reader"
    for live requests, "warmer" for the background warmer's small allowance).
    With ``block`` False (the card endpoints) misses translate in the
    background instead: the caller gets originals for them immediately and the
    next poll picks up the cached translations — a card never waits on a
    model call."""
    if not texts:
        return [], False

    # Reject unsupported targets up front: no model call, no cache key. This
    # bounds cache-key cardinality to the known locale set and defuses the
    # junk-target amplification vector on every path that translates (the public
    # /translate proxy and the ?lang= source/search/feed endpoints alike).
    if target not in _SUPPORTED_TARGETS:
        return list(texts), False
    if not gemini.configured() and settings.ANTHROPIC_API_KEY is None:
        return list(texts), False

    results: list[str] = list(texts)
    keys = [_cache_key(target, text) for text in texts]
    cached = await redis.mget(keys)

    misses = [
        i
        for i, value in enumerate(cached)
        if _decode(value) is None and _needs_model(texts[i], target)
    ]
    for i, value in enumerate(cached):
        decoded = _decode(value)
        if decoded is not None:
            results[i] = decoded

    if misses:
        miss_texts = [texts[i] for i in misses]
        miss_keys = [keys[i] for i in misses]
        if not block:
            if await redis.get(_failed_key(target, miss_texts)) is not None:
                # Parked after failing twice: serve originals — but stay
                # honest that the card is incomplete. pending=False here told
                # clients "done" and froze mixed-language cards for the whole
                # park; True keeps the card on its slow re-poll, which lands a
                # retry as soon as the park expires. The fast-poll budget on
                # the client is bounded, so this cannot re-poll-storm.
                return results, True
            deadline = time.monotonic() + _SOFT_WAIT_SECONDS
            task = await _start_background_translation(
                redis, miss_texts, miss_keys, target, budget
            )
            # Most batches land inside the soft wait, so cards usually render
            # translated on first view; a slow provider only costs the reader
            # one short re-poll, never a hung card.
            try:
                translated, lost = await asyncio.wait_for(
                    asyncio.shield(task), _SOFT_WAIT_SECONDS
                )
            except (TimeoutError, Exception):
                return results, True
            if lost and time.monotonic() < deadline:
                # Another poller is translating those chunks: wait on the
                # cache for them rather than serving originals straight away.
                waited = await _wait_for_cache(
                    redis, [miss_keys[idx] for idx in lost], deadline
                )
                for idx, value in zip(lost, waited, strict=True):
                    translated[idx] = value
            pending = False
            for idx, i in enumerate(misses):
                if translated[idx] is not None:
                    results[i] = translated[idx]  # type: ignore[assignment]
                else:
                    pending = True
            return results, pending
        translated, _, _ = await _translate_and_store(
            redis, miss_texts, miss_keys, target, budget
        )
        for idx, i in enumerate(misses):
            if translated[idx] is not None:
                results[i] = translated[idx]  # type: ignore[assignment]

    return results, False
