"""Machine translation for news headlines.

News comes from 250+ sources in many languages; a reader who picked a UI
language (or was geo-detected into one) wants the headlines in it too. A
language model translates them - the free tiers (Gemini, Groq, Ollama, NVIDIA,
then Mistral) first, the Anthropic API as the paid backup, the same split as
article summaries - and each ``(target, text)`` is cached in Redis, so any
given headline is translated at most once per language regardless of how many
readers see it.

Speed and cost: a card's headlines travel as a few small parallel batches, each
sent to whichever free provider has been answering fastest (see _generate), so
a cold card lands inside the request's soft wait. Cache reads are a single
Redis round-trip (``mget``), only the misses reach a model (a numbered list of
headlines in, the same-length list out), and a global daily cap on paid model
calls brakes the spend regardless of traffic. Freshly fetched feeds are also
translated ahead of their readers (see translate_ahead).
"""

import asyncio
import hashlib
import json
import re
import time
from collections.abc import Collection
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
# A week: card set sources repeat headlines across days, and a translation that
# is already right should not be bought again tomorrow.
_TTL_SECONDS = 7 * 24 * 60 * 60
# Paid (Anthropic) calls per day, split into two independent budgets so the
# background warmer can never starve readers: the reader budget covers live
# requests; the warmer budget is a small allowance that pre-fills the card set's
# translations when Gemini's free tier is spent.
# v2: counted on success only (the old keys were charged per attempt,
# including failures, and cannot be trusted for the day they were written).
_PAID_DAILY_KEY = "news:xlate:paid:v2:{budget}:{day}"
# The warmer's Gemini (free-tier) batches per day - see the config comment.
_WARMER_FREE_DAILY_KEY = "news:xlate:free:warmer:{day}"
# A reader asked for this language recently: the warmer keeps it warm. Without
# demand gating the warmer would translate the card set into every locale for
# readers who don't exist.
# Reader demand per language, in hourly buckets: the warmer ranks languages
# by how many card views asked for them over the last day, so a language with
# one reader a day never starves the one people are actually reading in.
DEMAND_KEY = "news:xlate:demand:{target}:{hour}"
DEMAND_TTL_SECONDS = 25 * 60 * 60
DEMAND_WINDOW_HOURS = 24
# A background batch already in flight for these exact texts - stops every
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
# originals and letting the batch finish in the background.
#
# Sized against production, not guessed. A cold 30-headline card was measured
# at two budgets and came back untranslated at BOTH:
#
#     budget   first response   translated inline?
#     1.5 s    1.72 s           no
#     2.5 s    2.74 s           no
#
# So the wait cannot win a cold card, and every extra tenth spent chasing one
# is latency the reader pays for nothing. Raising it to 2.5 s was tried and
# only made first paint a second slower.
#
# What the wait IS worth keeping for is the common top-up: a card already warm
# in this language with a few new headlines is one small call and does land
# inside a second. 1.0 s catches those, and a cold card falls through fast to
# the originals while the client's ramped re-poll (400/700/1100 ms) picks the
# batch up as soon as it lands. Cold cards are meant to be rare anyway: the
# warmer pre-translates the default set and recently-read sources.
_SOFT_WAIT_SECONDS = 1.0
# How often a poller waiting on someone else's in-flight batch re-reads the cache.
_CACHE_POLL_SECONDS = 0.25
# No reader waits on this (cards soft-wait then poll; the warmer runs in the
# background), so it only needs to be shorter than the pending claim. A third
# of 15-headline batches ran past 12 s in production and were thrown away.
_GEMINI_TIMEOUT_SECONDS = 25.0
# Headlines per model call: one feed's worth (feeds cap at 30 items), so a
# card costs two calls, not four.
#
# Eight was tried in production and made cold cards SLOWER, not faster. A
# smaller batch does return sooner in isolation, but the binding constraint
# here is per-minute provider quota, not model speed: halving the batch
# doubles the calls per card, the free tiers' minute slots run out sooner
# (news.translate_gemini_unavailable fired on most batches), and every card
# then queues behind the slow last-resort lane. Cold cards went from ~3 s to
# a 9.6 s median. Fewer, larger calls win whenever quota is what runs out.
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
    "hr": "Croatian (Latin script, standard Croatian vocabulary - never Serbian forms)",
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
# slipped mid-word) is a failure, not a result - better the original than
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


# Serbian is digraphic: Cyrillic and Gaj's Latin are the same language, letter
# for letter. The prompt asks for Cyrillic, but the model answers in Latin for
# roughly half the headlines, so one card carried two alphabets (measured in
# production: 15 of 30). Rejecting the Latin half would leave those headlines
# in ENGLISH, which is worse for a Serbian reader than Latin Serbian - so
# convert instead. The mapping is exact and standard (Pravopis), digraphs
# first so "nj"/"lj"/"dž" become one letter rather than two. No other language
# needs this: ru, uk and bg measured 30 of 30 in Cyrillic.
_SR_DIGRAPHS = (
    ("Dž", "Џ"), ("DŽ", "Џ"), ("dž", "џ"),
    ("Lj", "Љ"), ("LJ", "Љ"), ("lj", "љ"),
    ("Nj", "Њ"), ("NJ", "Њ"), ("nj", "њ"),
)  # fmt: skip
_SR_LETTERS = str.maketrans({
    "A": "А", "B": "Б", "V": "В", "G": "Г", "D": "Д", "Đ": "Ђ", "E": "Е",
    "Ž": "Ж", "Z": "З", "I": "И", "J": "Ј", "K": "К", "L": "Л", "M": "М",
    "N": "Н", "O": "О", "P": "П", "R": "Р", "S": "С", "T": "Т", "Ć": "Ћ",
    "U": "У", "F": "Ф", "H": "Х", "C": "Ц", "Č": "Ч", "Š": "Ш",
    "a": "а", "b": "б", "v": "в", "g": "г", "d": "д", "đ": "ђ", "e": "е",
    "ž": "ж", "z": "з", "i": "и", "j": "ј", "k": "к", "l": "л", "m": "м",
    "n": "н", "o": "о", "p": "п", "r": "р", "s": "с", "t": "т", "ć": "ћ",
    "u": "у", "f": "ф", "h": "х", "c": "ц", "č": "ч", "š": "ш",
})  # fmt: skip
_CYRILLIC_RE = re.compile("[Ѐ-ӿ]")
# A Latin letter welded straight onto a Cyrillic one inside a single word
# ("Технika", "Трамp"): the model reaching for the Latin key mid-word. A brand
# name is its own token ("Waymo ефекат") and Serbian spells a suffixed one with
# a hyphen ("iPhone-ов"), so neither trips this. Measured over live cards it
# fires on 2 of 108 Serbian headlines and 0 of 68 Russian, Ukrainian and
# Bulgarian ones.
_FUSED_LATIN_CYRILLIC_RE = re.compile(r"[A-Za-z][Ѐ-ӿ]|[Ѐ-ӿ][A-Za-z]")


def _mixed_cyrillic_word(text: str, target: str) -> bool:
    """True when a Cyrillic-script target came back with Latin fused mid-word.

    ``to_serbian_cyrillic`` deliberately returns a reply that already carries
    Cyrillic untouched, leaving "a mixed one for the script validator to
    reject" - but ``script_mismatch`` allows Latin everywhere, so nothing
    rejected it and the half-Latin word was cached for the 7-day TTL."""
    if _TARGET_SCRIPT.get(target) != "cyrillic":
        return False
    return _FUSED_LATIN_CYRILLIC_RE.search(text) is not None


def to_serbian_cyrillic(text: str) -> str:
    """Gaj's Latin Serbian rendered in Cyrillic. Text that already carries
    Cyrillic is returned untouched, so a correct reply is never re-processed
    and a mixed one is left for the script validator to reject."""
    if not text or _CYRILLIC_RE.search(text):
        return text
    for latin, cyrillic in _SR_DIGRAPHS:
        text = text.replace(latin, cyrillic)
    return text.translate(_SR_LETTERS)


# Scripts that do not put spaces between words, so a whole headline in them is
# a single "word" to str.split (Han, Hiragana, Katakana, Thai, Lao, Khmer,
# Burmese, Tibetan).
_SPACELESS_RE = re.compile(
    r"[⺀-鿿぀-ヿ豈-﫿฀-໿"
    r"ក-៿က-႟ༀ-࿿]"
)
# Characters of a spaceless script that make a headline a sentence rather than
# a title. Japanese headlines run 15-40 characters; a brand or proper noun that
# may legitimately echo is far shorter.
_SPACELESS_SENTENCE_CHARS = 10


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
    if len(source.split()) >= 4:
        return True
    # Japanese, Chinese and Thai headlines carry no word spaces, so the word
    # count above is always 1 for them and every echo slipped through: a whole
    # Japanese headline was cached as the Croatian translation for the 7-day
    # TTL, with the card reporting itself done. Measure those by length.
    spaceless = len(_SPACELESS_RE.findall(source))
    return spaceless >= _SPACELESS_SENTENCE_CHARS


# Latin letters incl. the accented planes European languages actually use.
_LATIN_CHARS = "A-Za-zÀ-ɏ"
_FUSED_SCRIPT_RE: dict[str, re.Pattern[str]] = {}


def script_mismatch(
    text: str, target: str, source: str = "", *, strict_fused: bool = False
) -> bool:
    """True when *text* contains characters of a script that is not the
    target language's - unless the *source* text carried them too (a name
    written in its own script stays as it was). Latin letters are allowed
    everywhere.

    A foreign character FUSED directly into a word of the target's own script
    ("jasne政策 okvire" on a Croatian card) is the model slipping mid-word -
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
            # source is a preserved name or unit ("小米SU7", "5μm"), not a slip -
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
    """en→en is the identity for English headlines - no model call, no cache
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
        " that language. Use only that language's standard script - never mix"
        " scripts within a headline. Write the simple, clear, natural headline"
        " a native news editor would - plain everyday words, never a stiff"
        " word-for-word rendering, with correct grammar and agreement."
        " Translate every ordinary word; only proper nouns, brand names and"
        " established loanwords stay untranslated. Use that language's own"
        " standard vocabulary - never forms borrowed from a neighbouring"
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


# Recent reply time per free provider (exponential moving average, ms). The
# reader path asks the fastest one first: measured live, Gemini flash-lite
# needed 2.5-3 s for a batch while Groq and Ollama (gpt-oss-120b) answer in
# about a second, so a cold card that used to miss the 1.5 s soft wait lands
# inside it. Quality is unaffected: gpt-oss-120b is the stronger model of the
# two, the prompt and validators are the same for every provider, and the
# last free line (Mistral's 8B) stays a last resort as before.
_LATENCY_KEY = "news:xlate:latency:{provider}"
_LATENCY_TTL_SECONDS = 6 * 60 * 60
# Untried providers are assumed this fast, so a fresh deploy keeps the
# configured order until real numbers arrive.
_LATENCY_DEFAULT_MS = 1500
_LATENCY_SMOOTHING = 0.3
# Free providers the reader path spreads across, in tie-break order. NVIDIA
# (Kimi K3, 5-7 s a batch) is last among them: better Croatian than Mistral's
# 8B but slower, so a reader only lands on it when the quick lines are out.
_FAST_FREE_PROVIDERS = ("gemini", "groq", "ollama", "cloudflare")
_LAST_RESORT_FREE_PROVIDERS = frozenset({"mistral"})
# The OpenAI-compatible lines the warmer may use (see _generate). NVIDIA is
# background-ONLY: its shared free queue swung between 2 and 20 s a batch in
# live runs, unpredictable for a reader but irrelevant here, where nobody
# waits and its strong Croatian/Slovenian is what counts. Every batch it and
# Cloudflare take is Gemini or Groq quota kept for readers.
_WARMER_FREE_LLM_PROVIDERS = frozenset({"nvidia", "ollama", "cloudflare", "groq"})
# A reader's batch is hedged: when the lane it went to has not answered in
# this long, the next lane is started in parallel and the first good reply
# wins (the other attempt is cancelled). Quality is untouched: same prompt,
# same validators, whichever lane answers.
#
# This must stay well ABOVE a normal reply, or it stops being a safety net
# and becomes a load multiplier: at 2.5 s it fired on 26 of 36 production
# batches, doubling the calls against the very per-minute quotas that were
# already the bottleneck, and cold cards got slower.
#
# The threshold must sit ABOVE the median of the slowest lane in regular use
# and BELOW its p90, so it skips normal replies and only rescues stragglers.
# From 12 h of production (1443 batches): gemini 1.1 s and groq 1.0 s, but
# ollama and cloudflare - together ~46% of volume - run a 5.2 s median with a
# 16-20 s p90, and that tail is what strands a cold card.
#
# 4 s was tried and is below that 5.2 s median, so it fired on 67% of batches:
# the same load-multiplier regime as 2.5 s, not a safety net. 6 s clears the
# median with margin while still catching the 16-20 s stragglers.
_HEDGE_AFTER_SECONDS = 6.0


async def _note_latency(redis: Redis, provider: str, ms: int) -> None:
    key = _LATENCY_KEY.format(provider=provider)
    previous = await redis.get(key)
    if previous is None:
        value = ms
    else:
        value = int((1 - _LATENCY_SMOOTHING) * int(previous) + _LATENCY_SMOOTHING * ms)
    await redis.set(key, str(value), ex=_LATENCY_TTL_SECONDS)


async def reader_provider_order(redis: Redis) -> list[str]:
    """The configured fast free providers, quickest recent reply first."""
    configured = {endpoint.provider for endpoint in free_llm.endpoints()}
    if gemini.configured():
        configured.add("gemini")
    candidates = [p for p in _FAST_FREE_PROVIDERS if p in configured]
    if len(candidates) < 2:
        return candidates
    values = await redis.mget([_LATENCY_KEY.format(provider=p) for p in candidates])
    latency = {
        p: int(v) if v is not None else _LATENCY_DEFAULT_MS
        for p, v in zip(candidates, values, strict=True)
    }
    # Stable: equal (or unknown) latencies keep the configured order.
    return sorted(candidates, key=lambda p: latency[p])


# Keys to try before a batch gives up on Gemini and drops to the next provider.
#
# Key SELECTION already skips benched keys, but a key that dies mid-call used to
# take the whole batch off Gemini with it, even with thirteen healthy keys in the
# pool. A key spending its daily quota is discovered by one failed call, so that
# one death was pushing batches onto slower free lanes and, when those were out,
# onto the paid card.
#
# Small on purpose. The neighbours are usually fine, so a second key almost
# always settles it, while a real Gemini-wide outage must not walk all fourteen
# keys one timeout at a time. The warmer can afford one probe more than a reader,
# who is being waited on.
_GEMINI_KEY_ATTEMPTS = 2
_GEMINI_KEY_ATTEMPTS_WARMER = 3


async def _try_gemini(
    redis: Redis, system: str, user: str, budget: str, started: float
) -> str | None:
    """One Gemini attempt; None when no key is usable or the call failed (the
    key is benched by then). Raises nothing."""
    if not gemini.configured():
        return None
    day = datetime.now(UTC).strftime("%Y%m%d")
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
    probes = _GEMINI_KEY_ATTEMPTS_WARMER if budget == "warmer" else _GEMINI_KEY_ATTEMPTS
    for probe in range(probes):
        slot = await _acquire_gemini(redis, budget) if free_ok else None
        if slot is None:
            # Only the FIRST miss is worth a line: after a failed probe the
            # pool being empty is the expected tail of the same event.
            if free_ok and probe == 0:
                log.info("news.translate_gemini_unavailable", budget=budget)
            return None
        index, key = slot
        attempt = time.monotonic()
        try:
            text = await _generate_gemini(system, user, key)
            if not text:
                raise ValueError("empty translation")
        except (httpx.HTTPError, ValueError) as exc:
            seconds = await gemini.note_failure(redis, index, exc)
            log.info(
                "news.translate_gemini_fallback",
                error=str(exc) or type(exc).__name__,
                cooldown=seconds,
                probe=probe,
            )
            # The dead key is benched now, and `acquire` round-robins, so the
            # next probe lands on a different one.
            continue
        if budget == "warmer":
            spent = await _count(redis, _WARMER_FREE_DAILY_KEY.format(day=day))
            if spent == settings.TRANSLATION_WARMER_FREE_DAILY_CAP:
                log.info("news.translate_warmer_free_cap", used=spent)
        # Learned latency is this provider's own reply time; the logged ms is
        # the whole batch including any provider tried and failed before it.
        await _note_latency(redis, "gemini", int((time.monotonic() - attempt) * 1000))
        log.info(
            "news.translate_batch",
            provider="gemini",
            budget=budget,
            ms=int((time.monotonic() - started) * 1000),
        )
        return text
    return None


async def _try_free_llm(
    redis: Redis,
    system: str,
    user: str,
    budget: str,
    started: float,
    providers: Collection[str] | None,
) -> str | None:
    """One attempt on the OpenAI-compatible free pool (narrowed to
    *providers* when given); None when nothing is usable or the call failed
    (the endpoint is benched by then). Not gated on the warmer's Gemini share:
    that cap divides the GEMINI fleet between warming and readers; these
    endpoints are bounded by their own provider quotas and benching."""
    endpoint = await free_llm.acquire(redis, providers)
    if endpoint is None:
        return None
    attempt = time.monotonic()
    try:
        text = await free_llm.generate(system, user, endpoint)
        if not text:
            raise ValueError("empty translation")
    except (httpx.HTTPError, ValueError) as exc:
        await free_llm.note_failure(redis, endpoint, exc)
        log.info(
            "news.translate_free_llm_fallback",
            endpoint=endpoint.id,
            error=str(exc) or type(exc).__name__,
        )
        return None
    await _note_latency(
        redis, endpoint.provider, int((time.monotonic() - attempt) * 1000)
    )
    log.info(
        "news.translate_batch",
        provider=endpoint.provider,
        budget=budget,
        ms=int((time.monotonic() - started) * 1000),
    )
    return text


async def _attempt(
    redis: Redis,
    system: str,
    user: str,
    budget: str,
    started: float,
    lane: Collection[str] | None,
) -> str | None:
    """One attempt on *lane*: Gemini's key pool, or the named OpenAI-compatible
    providers. None when the lane had nothing usable or failed."""
    if lane is not None and "gemini" in lane:
        return await _try_gemini(redis, system, user, budget, started)
    return await _try_free_llm(redis, system, user, budget, started, lane)


async def _hedged(
    redis: Redis,
    system: str,
    user: str,
    budget: str,
    started: float,
    lanes: list[Collection[str] | None],
) -> str | None:
    """Run *lanes* in order, hedged (see _HEDGE_AFTER_SECONDS): the next lane
    starts when the current one is still silent after the hedge delay, or at
    once when it came back empty; the first text wins and every other attempt
    still in flight is cancelled. Returns None only when every lane failed."""
    pending: set[asyncio.Task[str | None]] = set()
    next_lane = 0
    while next_lane < len(lanes) or pending:
        if next_lane < len(lanes):
            lane = lanes[next_lane]
            next_lane += 1
            pending.add(
                asyncio.create_task(
                    _attempt(redis, system, user, budget, started, lane)
                )
            )
        # Wait for something to finish, or for the hedge delay to pass so the
        # next lane joins the race; once every lane is running, wait for real.
        timeout = _HEDGE_AFTER_SECONDS if next_lane < len(lanes) else None
        done, pending = await asyncio.wait(
            pending, timeout=timeout, return_when=asyncio.FIRST_COMPLETED
        )
        for task in done:
            text = task.result()
            if text:
                for other in pending:
                    other.cancel()
                if pending:
                    log.info("news.translate_hedge_won", cancelled=len(pending))
                return text
    return None


async def _generate(redis: Redis, system: str, user: str, budget: str) -> str:
    """Free tiers first, paid backup last. A reader's batch goes to whichever
    fast free provider has been answering quickest (see _LATENCY_KEY), then
    the others, then the last-resort free line, each hedged against the next
    (see _hedged) so a slow lane never holds a card; the warmer keeps Gemini first
    (it has the largest quota and nobody is waiting on it). Anthropic picks
    up what no free line could - against the caller's own daily paid budget
    ("reader" or "warmer"), so background warming can never starve live
    readers. Paid calls are counted when they succeed, so a provider error
    never eats the day's allowance."""
    started = time.monotonic()
    day = datetime.now(UTC).strftime("%Y%m%d")
    if budget == "reader":
        lanes: list[Collection[str] | None] = [
            *({p} for p in await reader_provider_order(redis)),
            _LAST_RESORT_FREE_PROVIDERS,
        ]
        text = await _hedged(redis, system, user, budget, started, lanes)
        if text:
            return text
    else:
        text = await _try_gemini(redis, system, user, budget, started)
        if text:
            return text
        # The warmer never touches the last-resort line: Mistral's plan meters
        # about one request a second, and in production the out-of-budget
        # warmer was draining that minute by minute, so readers' own batches
        # found it minute-full and starved (hundreds of parked batches a day).
        text = await _try_free_llm(
            redis, system, user, budget, started, _WARMER_FREE_LLM_PROVIDERS
        )
        if text:
            return text
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
    documents (rate limit, overloaded, gateway) - a burst must not turn into
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
        # Echo detection must see the RAW reply. Transliterating first rewrote
        # an echoed English headline into Cyrillic letter-by-letter
        # ("Trump says he will" -> "Трумп саyс хе wилл"), which no longer
        # equals the source, so the echo guard passed it and `script_mismatch`
        # could not see Latin inside Cyrillic either. The gibberish was then
        # cached as Serbian for the full 7-day TTL.
        echoes = [
            item is not None and _echoed_source(item, source, target)
            for item, source in zip(items, texts)
        ]
        if target == "sr":
            # After the echo check, before `script_mismatch`: Latin Serbian is
            # a correct translation in the wrong alphabet, and converting it
            # keeps the card in one script (see to_serbian_cyrillic).
            items = [
                to_serbian_cyrillic(item) if item is not None else None
                for item in items
            ]
        clean = [
            None
            if item is not None
            and (
                script_mismatch(item, target, source)
                or echo
                or _mixed_cyrillic_word(item, target)
            )
            else item
            for item, source, echo in zip(items, texts, echoes)
        ]
        # An echo can be the CORRECT translation (the prompt says to leave
        # proper-noun headlines and already-target-language text unchanged),
        # but treating every echo as a failure made those rejections
        # deterministic: never cached, re-bought on every poll in every
        # language, forever - the standing budget drain behind the frozen
        # part-English cards. Ask once more for just the echoed items: a
        # DIFFERENT reply wins, and a second identical echo is accepted as
        # the model insisting - either way the value caches and the loop ends.
        echoed = [
            i
            for i, (item, source, echo) in enumerate(zip(items, texts, echoes))
            if echo
            and clean[i] is None
            and item is not None
            and not script_mismatch(item, target, source)
        ]
        if echoed:
            # Isolated: a retry failure (unparsable, capacity) must not throw
            # away the good translations already in `clean` - that would
            # recreate the re-buy loop this block exists to end.
            try:
                retry_texts = [texts[i] for i in echoed]
                async with _semaphore:
                    retried = await _generate_parsed(redis, retry_texts, target, budget)
                for slot, item in zip(echoed, retried):
                    if item is None:
                        continue
                    # A second identical echo is the model insisting the
                    # headline is already right; cache the SOURCE so the batch
                    # stops being re-bought every poll. Never transliterate it
                    # on the way: converting an echoed English sentence
                    # letter-by-letter produces Cyrillic nonsense
                    # ("Трумп саyс хе wилл"), which is what this branch exists
                    # to avoid caching.
                    if _echoed_source(item, texts[slot], target):
                        clean[slot] = texts[slot]
                        continue
                    # A genuine new translation: convert, then validate, the
                    # same order as the first pass. Skipping the conversion
                    # here cached a correct Latin-Serbian retry beside 14
                    # Cyrillic neighbours - the mixed-alphabet card
                    # to_serbian_cyrillic exists to prevent.
                    if target == "sr":
                        item = to_serbian_cyrillic(item)
                    if script_mismatch(
                        item, target, texts[slot]
                    ) or _mixed_cyrillic_word(item, target):
                        continue
                    clean[slot] = item
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
        # `budget` says whose batch went hungry: "reader" is a card a person
        # is looking at, "warmer" is background work nobody waits on. Without
        # it a starved count could only be attributed by guessing from which
        # container logged it.
        log.info("news.translate_starved", target=target, budget=budget, error=str(exc))
        raise
    except (httpx.HTTPError, ValueError) as exc:
        log.info("news.translate_failed", target=target, budget=budget, error=str(exc))
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


async def demanded_targets(redis: Redis, *, min_total: int = 0) -> list[str]:
    """Languages readers asked for in the last day, most-requested first.

    ``min_total`` filters out languages below a daily request floor: real
    readers generate hundreds of demand stamps a day (the wall polls every
    visible card), so a floor tells genuine audiences apart from one caller
    cycling ?lang= codes to steer budget toward languages nobody reads."""
    targets = sorted(t for t in _SUPPORTED_TARGETS if t != "en")
    hours = _demand_hours()
    keys = [DEMAND_KEY.format(target=t, hour=h) for t in targets for h in hours]
    values = await redis.mget(keys)
    ranked: list[tuple[int, str]] = []
    for i, target in enumerate(targets):
        window = values[i * len(hours) : (i + 1) * len(hours)]
        total = sum(int(v) for v in window if v is not None)
        if total > max(0, min_total - 1):
            ranked.append((total, target))
    ranked.sort(key=lambda pair: (-pair[0], pair[1]))
    return [target for _, target in ranked]


# Per-source language demand: the languages readers opened THIS source in over
# the last day. Drives translate-ahead: when a feed refreshes, its headlines
# are translated into those languages in the background right then, so a
# returning reader finds the card warm instead of paying the model round trip
# (measured live: originals at the 1.5 s soft wait, translations 1-2 s later).
# The card set warmer covers only the default card set; a reader's own followed sources
# had no warming at all. Bounded on both axes so a caller cycling ?lang= across
# sources cannot buy translations nobody reads: a language needs more than one
# hit in the window, and only the top few per source qualify.
SOURCE_LANG_DEMAND_KEY = "news:xlate:srcdemand:{source}"
SOURCE_LANG_DEMAND_TTL_SECONDS = 24 * 60 * 60
_AHEAD_MIN_HITS = 2
_AHEAD_MAX_TARGETS = 3


async def note_source_language_demand(
    redis: Redis, source_id: str, target: str
) -> None:
    """A reader opened *source_id* in *target*: count it for translate-ahead."""
    if target not in _SUPPORTED_TARGETS or target == "en":
        return
    key = SOURCE_LANG_DEMAND_KEY.format(source=source_id)
    async with redis.pipeline(transaction=False) as pipe:
        pipe.hincrby(key, target, 1)
        pipe.expire(key, SOURCE_LANG_DEMAND_TTL_SECONDS)
        await pipe.execute()


async def source_demanded_targets(redis: Redis, source_id: str) -> list[str]:
    """Languages worth translating *source_id* into ahead of a reader, most
    requested first: at least ``_AHEAD_MIN_HITS`` in the window, at most
    ``_AHEAD_MAX_TARGETS`` of them."""
    raw = await redis.hgetall(SOURCE_LANG_DEMAND_KEY.format(source=source_id))
    ranked: list[tuple[int, str]] = []
    for field, value in raw.items():
        target = field.decode() if isinstance(field, bytes) else str(field)
        hits = int(value)
        if target in _SUPPORTED_TARGETS and hits >= _AHEAD_MIN_HITS:
            ranked.append((hits, target))
    ranked.sort(key=lambda pair: (-pair[0], pair[1]))
    return [target for _, target in ranked[:_AHEAD_MAX_TARGETS]]


_ahead_tasks: set[asyncio.Task[None]] = set()


async def translate_ahead(
    redis: Redis, source_id: str, texts: list[str], *, skip: str | None = None
) -> None:
    """Translate a freshly fetched card into the languages its readers use,
    except *skip* (the language the current request translates itself).
    Cache-first, and single-flight per chunk like every other path, so a
    reader arriving mid-run waits on the same batch rather than buying it
    again. Failures are logged, never raised: this is best effort ahead of a
    reader who may never come."""
    if not texts:
        return
    # The demand read is inside the guard too: this runs as a detached task,
    # so an exception escaping here would be an unretrieved task exception
    # (logged by the loop at GC time, at best) rather than a handled miss.
    try:
        targets = await source_demanded_targets(redis, source_id)
    except Exception as exc:
        log.info(
            "news.translate_ahead_failed",
            source=source_id,
            error=str(exc) or type(exc).__name__,
        )
        return
    for target in targets:
        if target == skip:
            continue
        try:
            # The warmer's budget, not the reader's: this is background work
            # by definition, and on the reader budget it competed with live
            # cards for the very per-minute slots that are the bottleneck.
            await translate_texts(redis, texts, target, budget="warmer")
        except Exception as exc:
            log.info(
                "news.translate_ahead_failed",
                source=source_id,
                target=target,
                error=str(exc) or type(exc).__name__,
            )


def spawn_translate_ahead(
    redis: Redis, source_id: str, texts: list[str], *, skip: str | None = None
) -> None:
    """Fire-and-forget :func:`translate_ahead` for the request path (the
    response must not wait on it). Tasks are held so they are not collected
    mid-flight; ``drain_translate_ahead`` awaits them where the loop is about
    to end (the warmer)."""
    task = asyncio.create_task(translate_ahead(redis, source_id, texts, skip=skip))
    _ahead_tasks.add(task)
    task.add_done_callback(_ahead_tasks.discard)


async def drain_translate_ahead(timeout: float | None = None) -> None:
    """Await outstanding translate-ahead tasks (bounded by *timeout*)."""
    pending = list(_ahead_tasks)
    if not pending:
        return
    await asyncio.wait(pending, timeout=timeout)


async def warmer_out_of_budget(redis: Redis) -> bool:
    """True when the warmer has spent both its free-tier share and its paid
    allowance for the day. A broke warmer MUST stand down entirely: its
    retries still seized the per-chunk single-flight claims and then failed,
    which locked live readers - whose own paid budget was still available -
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
    # Gemini share and paid allowance both spent - but the second free line
    # may still serve, so the warmer only stands down when that is out too.
    # Only the lines the warmer is allowed to use count (never Mistral).
    return not await free_llm.available(redis, _WARMER_FREE_LLM_PROVIDERS)


async def paid_used(redis: Redis, budget: str) -> int:
    """Paid batches *budget* has spent today."""
    key = _PAID_DAILY_KEY.format(
        budget=budget, day=datetime.now(UTC).strftime("%Y%m%d")
    )
    return int(await redis.get(key) or 0)


class NoTranslationCapacity(ValueError):
    """No provider could take the batch right now: Gemini benched or timing
    out with no paid backup, or the paid allowance for the day spent."""


# Keys per MGET. Redis is single-threaded, so one giant MGET blocks every
# other client for its whole duration. The batch endpoint calls this with a
# headline per item - up to 7,700 for a maxed request, ~285 KB of key names in
# one command - on the route whose entire purpose is an instant first paint.
# 250 matches the discipline already used by search, followed_feed and the
# heatmap readers.
_MGET_CHUNK = 250


async def _mget_chunked(redis: Redis, keys: list[str]) -> list[object]:
    """`MGET` *keys* in bounded chunks, preserving order."""
    values: list[object] = []
    for start in range(0, len(keys), _MGET_CHUNK):
        values.extend(await redis.mget(keys[start : start + _MGET_CHUNK]))
    return values


async def cached_translations_pending(
    redis: Redis, texts: list[str], target: str
) -> tuple[list[str], list[int]]:
    """:func:`cached_translations` plus the indices still waiting on a model.

    For callers that must not start work themselves (the batch endpoint exists
    to make a warm wall paint instantly and never fetches): they serve what is
    cached, and the indices let the client keep polling until the card's own
    request fills the rest, instead of pinning English on the wall.

    Indices, not a single flag, because a batch spans many sources and each
    card reports its own state. Callers must not infer this from "the text
    came back unchanged": for a brand name or a headline already in the target
    language the correct translation IS the original, so that test marked
    warm cards pending forever and left the wall polling for work that was
    already done."""
    if not texts or target not in _SUPPORTED_TARGETS:
        return list(texts), []
    results = list(texts)
    pending: list[int] = []
    cached = await _mget_chunked(redis, [_cache_key(target, t) for t in texts])
    for i, value in enumerate(cached):
        decoded = _decode(value)
        if decoded is not None:
            results[i] = decoded
        elif _needs_model(texts[i], target):
            pending.append(i)
    return results, pending


async def cached_translations(redis: Redis, texts: list[str], target: str) -> list[str]:
    """Cache hits only - misses come back as the original text, and nothing
    reaches a model or writes a key. This is what the public /translate proxy
    serves: its texts are caller-supplied, and translating those cached each
    model reply under the genuine headline's hash, so one crafted batch could
    poison every reader's translation of a real headline for a week (and the
    same route drained the shared daily budget). First-party clients never
    call it - cards translate server-side - so cache-only costs nothing."""
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
    indices whose chunk was already in flight for another poller - those come
    back None here and appear in the cache when that poller's write lands -
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
        # poller arriving mid-flight computes a *smaller* miss list - so a
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
        # _FAILED_KEY); one whose chunks were merely claimed elsewhere is not -
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
    next poll picks up the cached translations - a card never waits on a
    model call."""
    if not texts:
        return [], False

    # Reject unsupported targets up front: no model call, no cache key. This
    # bounds cache-key cardinality to the known locale set and defuses the
    # junk-target amplification vector on every path that translates (the public
    # /translate proxy and the ?lang= source/search/feed endpoints alike).
    if target not in _SUPPORTED_TARGETS:
        return list(texts), False
    # The free pool counts as a provider here, as it does everywhere else in
    # the pipeline (see _generate's lanes and the equivalent guards in
    # summary.py). Leaving it out meant a deployment with Groq or Ollama keys
    # but no Gemini and no Anthropic served every card, search and feed in the
    # original language with translationsPending False - so the client never
    # re-polled - while those providers sat idle.
    if (
        not gemini.configured()
        and not free_llm.configured()
        and settings.ANTHROPIC_API_KEY is None
    ):
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
                # Parked after failing twice: serve originals - but stay
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
