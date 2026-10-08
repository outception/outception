"""One-tap article summaries. Tapping a headline opens a short summary of
the article with the source link underneath. The article body is fetched
through the guarded fetcher, reduced to readable text and written up by
the generation chain. Summaries cache per (url, lang) for a week, one
model call per article, and the daily budget brakes the spend regardless
of traffic."""

import asyncio
import json
from collections.abc import AsyncIterator, Awaitable
from dataclasses import dataclass
from typing import Literal

import httpx
import structlog

from outception.config import settings
from outception.redis import Redis

from .. import cache as news_cache
from .. import gnews
from ..fetch import NewsFetchError
from . import budget
from .errors import (
    LiveDeadlinePassed,
    NoArticleText,
    SummariesNotConfigured,
    SummaryUnavailable,
)
from .extract import is_unsummarizable, resolved_article_text
from .prompts import NO_ARTICLE, script_mismatch, scrub_style, system_prompt
from .providers.chain import ChainExhausted
from .providers.classes import ModelError
from .providers.lanes import Consumer, Lane
from .providers.registry import any_configured, build_chains
from .queue import note_warm_candidate
from .teaser import TEASER_JUNK, clean_teaser

log = structlog.get_logger()

# Single-flight: taps on the same (url, lang) while one is generating wait
# for its cache write instead of each paying for a model call of their own.
PENDING_KEY = "news:summary:pending:{digest}"
PENDING_TTL_SECONDS = 30
PENDING_POLL_SECONDS = 0.25
# The panel gives up on an empty stream after ten seconds, and a reader
# who has watched it that long has already lost. A live tap gets this long
# to have the article in hand and this much more for the model to start
# writing; past either, the reader is sent to the article at once and the
# summary is finished by the warmer, so the next tap finds it cached.
LIVE_ARTICLE_SECONDS = 6.0
LIVE_FIRST_CHUNK_SECONDS = 6.0
# Whole-generation bound for the non-streaming (app) path, which has no
# first-token signal to work with.
LIVE_MODEL_SECONDS = 8.0
# Whole-stream bound for the streaming (web) path: the client's timeout is
# per read, not per stream, so without it a trickling model had no ceiling.
LIVE_STREAM_SECONDS = LIVE_FIRST_CHUNK_SECONDS + LIVE_MODEL_SECONDS
# How long a duplicate tap waits on the leader's single-flight generation.
# It must clear the leader's own ceiling on either path plus the scrub and
# cache write after it, or a waiter times out in the same breath as the
# result arrives. Derived, not written, so raising a deadline cannot
# silently reintroduce that race.
PENDING_WAIT_SECONDS = (
    LIVE_ARTICLE_SECONDS + max(LIVE_MODEL_SECONDS, LIVE_STREAM_SECONDS) + 2.0
)
# The marker must outlive the wait or it expires under a waiter still
# watching it, which is the single-flight collapsing into duplicates.
assert PENDING_WAIT_SECONDS < PENDING_TTL_SECONDS
# The warmer's whole-run bound per candidate: the fetcher's per-operation
# timeout compounds over retries, redirects and the reader fallback.
WARM_TIMEOUT_SECONDS = 45

SummaryKind = Literal["summary", "teaser"]

# What a generation can raise that should fail-mark the article rather
# than crash the request.
GENERATION_FAILURES = (
    NewsFetchError,
    ModelError,
    httpx.HTTPError,
    httpx.StreamError,
    ValueError,
    json.JSONDecodeError,
)


@dataclass(frozen=True)
class SummaryResult:
    text: str
    kind: SummaryKind


def _decoded(value: bytes | str | None) -> str | None:
    if value is None:
        return None
    return value.decode() if isinstance(value, bytes) else value


def _acceptable(url: str) -> bool:
    return url.startswith(("http://", "https://")) and not is_unsummarizable(url)


async def generate_text(
    redis: Redis, text: str, lane: Lane, *, consumer: Consumer | None = None
) -> str:
    """One pass of the generation chain over the article text. The seam
    the tests stand in for."""
    reply = await build_chains(redis).generate(
        text, lane, system=system_prompt(), consumer=consumer
    )
    return reply.text


def stream_text(redis: Redis, text: str, lane: Lane) -> AsyncIterator[str]:
    return build_chains(redis).stream(text, lane, system=system_prompt())


async def _produce(
    redis: Redis,
    url: str,
    lang: str,
    *,
    lane: Lane,
    live: bool = False,
    pretap: bool = False,
) -> str:
    """Fetch the article and produce its scrubbed summary. Raises the
    generation failures on anything that should fail-mark the article.

    `live` puts the article fetch and the generation on the deadlines a
    watching reader allows; the background warmer keeps the unbounded
    fetch, since nobody is watching it."""
    if live:
        try:
            text = await asyncio.wait_for(
                resolved_article_text(redis, url), LIVE_ARTICLE_SECONDS
            )
        except TimeoutError as exc:
            raise LiveDeadlinePassed("article not fetched in time") from exc
    else:
        text = await resolved_article_text(redis, url)
    warm = lane == Lane.background
    await budget.charge_daily(redis, warm=warm, pretap=pretap)
    consumer = Consumer.warm if warm else None

    def generate_once() -> Awaitable[str]:
        return generate_text(redis, text, lane, consumer=consumer)

    if live:
        # The fetch is bounded above; bound the generation too, and hand
        # off: the urgent warm queue finishes the same summary with nobody
        # waiting, so the next tap is a cache hit.
        try:
            summary = await asyncio.wait_for(generate_once(), LIVE_MODEL_SECONDS)
        except TimeoutError as exc:
            raise LiveDeadlinePassed("model did not finish in time") from exc
    else:
        summary = await generate_once()
    if not summary:
        raise NewsFetchError("empty summary")
    # The model's refusal sentinel: the fetched page was not the article.
    # Fail-mark instead of caching a line about cookie notices for a week.
    if NO_ARTICLE in summary[:40]:
        raise NewsFetchError("fetched page is not the article")
    if script_mismatch(summary, text):
        # The model slipped a character from another script: one more try,
        # then treat it as a transient failure rather than show garbage.
        log.info("news.summary_script_mismatch", lang=lang)
        if live:
            # A second full generation costs more than the time a watching
            # reader has left; the warmer still gets its retry.
            raise ValueError("mixed script in summary")
        summary = await generate_once()
        if not summary or script_mismatch(summary, text):
            raise ValueError("mixed script in summary")
    return scrub_style(summary)


async def _cached_result(redis: Redis, digest: str) -> SummaryResult | None:
    summary, teaser = await redis.mget(
        [
            budget.CACHE_KEY.format(digest=digest),
            budget.TEASER_CACHE_KEY.format(digest=digest),
        ]
    )
    cached = _decoded(summary)
    if cached is not None:
        return SummaryResult(cached, "summary")
    held = _decoded(teaser)
    if held is not None:
        if TEASER_JUNK.search(held):
            # Poisoned before the junk filter existed: drop it so the next
            # tap rebuilds from a clean source.
            await redis.delete(budget.TEASER_CACHE_KEY.format(digest=digest))
            return None
        return SummaryResult(held, "teaser")
    return None


async def has_cached(redis: Redis, url: str, lang: str) -> bool:
    """Whether a finished result (summary or publisher teaser) for this
    url and lang is already cached: serving it costs neither a fetch nor a
    model call, so the callers' guards may wave it through."""
    return await _cached_result(redis, budget.digest(url, lang)) is not None


async def _teaser_result(
    redis: Redis, url: str, digest: str, exc: BaseException | None
) -> SummaryResult | None:
    """The publisher's own standfirst, when we have one: the feed's
    description first, else what the page exposed. No model call at all:
    these run exactly on the paths that exist because the budget is spent
    or the article failed, so they must never be the thing that spends
    more."""
    teaser = clean_teaser(await news_cache.get_teaser(redis, url))
    if teaser is None and isinstance(exc, NoArticleText):
        teaser = clean_teaser(exc.teaser)
    if not teaser:
        return None
    await redis.set(
        budget.TEASER_CACHE_KEY.format(digest=digest),
        teaser,
        ex=budget.TEASER_CACHE_TTL_SECONDS,
    )
    log.info("news.summary_teaser", url=url)
    return SummaryResult(teaser, "teaser")


async def _await_pending(redis: Redis, digest: str) -> SummaryResult:
    """Wait for the in-flight generation of this digest to land in the
    cache. Gives up as soon as the marker is gone without a result (the
    producer failed) or after the wait budget."""
    deadline = asyncio.get_running_loop().time() + PENDING_WAIT_SECONDS
    pending_key = PENDING_KEY.format(digest=digest)
    while True:
        result = await _cached_result(redis, digest)
        if result is not None:
            return result
        if (
            await redis.get(pending_key) is None
            or asyncio.get_running_loop().time() > deadline
        ):
            raise SummaryUnavailable()
        await asyncio.sleep(PENDING_POLL_SECONDS)


async def _brake(redis: Redis, url: str, digest: str) -> SummaryResult | None:
    """The daily budget and the per-URL fan-out cap, read before a
    generation. Returns the teaser to serve instead when a brake is on,
    `SummaryUnavailable` when there is none, and None when the generation
    may run."""
    used = await budget.daily_used(redis)
    if used >= settings.SUMMARY_DAILY_CAP:
        log.warning("news.summary_daily_cap", used=used)
    elif not await budget.url_fanout_exceeded(redis, url):
        return None
    result = await _teaser_result(redis, url, digest, None)
    if result is None:
        raise SummaryUnavailable()
    return result


async def _generate(redis: Redis, url: str, lang: str, digest: str) -> SummaryResult:
    braked = await _brake(redis, url, digest)
    if braked is not None:
        return braked
    try:
        summary = await _produce(redis, url, lang, lane=Lane.interactive, live=True)
    except GENERATION_FAILURES as exc:
        log.info("news.summary_failed", url=url, error=str(exc))
        await budget.mark_failed(redis, url, digest, exc)
        if isinstance(exc, LiveDeadlinePassed):
            # Hand the slow article to the warmer: the reader is already
            # gone, but the next tap should find it cached.
            await note_warm_candidate(redis, url, lang, urgent=True)
        result = await _teaser_result(redis, url, digest, exc)
        if result is None:
            raise SummaryUnavailable() from exc
        return result
    await budget.mark_succeeded(redis, url, digest, summary)
    return SummaryResult(summary, "summary")


async def get_summary_result(redis: Redis, url: str, lang: str) -> SummaryResult:
    """The article's summary, cache-first (one model call per url and
    lang), or, when the article is out of reach, the publisher's own
    teaser."""
    if not any_configured():
        raise SummariesNotConfigured()
    if not _acceptable(url):
        raise SummaryUnavailable()
    digest = budget.digest(url, lang)
    cached = await _cached_result(redis, digest)
    if cached is not None:
        return cached
    if await redis.get(budget.FAIL_KEY.format(digest=digest)) is not None or (
        await budget.host_blocked(redis, url)
    ):
        # Known not to summarize: no fetch, but the feed's standfirst still
        # serves.
        result = await _teaser_result(redis, url, digest, None)
        if result is None:
            raise SummaryUnavailable()
        return result
    pending_key = PENDING_KEY.format(digest=digest)
    if not await redis.set(pending_key, "1", ex=PENDING_TTL_SECONDS, nx=True):
        return await _await_pending(redis, digest)
    try:
        return await _generate(redis, url, lang, digest)
    finally:
        await redis.delete(pending_key)


async def get_summary(redis: Redis, url: str, lang: str) -> str:
    return (await get_summary_result(redis, url, lang)).text


async def is_available(redis: Redis, url: str, lang: str) -> bool:
    """Whether a tap on this headline can expect a summary, decided from
    what is already known (cache, failure markers, budget, provider
    state), never by fetching or calling a model. False means the reader
    should be sent to the article at once; True is a prognosis, not a
    promise."""
    if not any_configured() or not _acceptable(url):
        return False
    digest = budget.digest(url, lang)
    day = budget.today()
    name = budget.host(url)
    # Every one of these is independent, so they are read in one round
    # trip: this runs on every headline tap.
    keys = [
        budget.CACHE_KEY.format(digest=digest),
        budget.TEASER_CACHE_KEY.format(digest=digest),
        news_cache.teaser_key(url),
        budget.FAIL_KEY.format(digest=digest),
        budget.DAILY_KEY.format(day=day),
        # The summary allowlist (headlines the wall has served).
        news_cache.known_key(url),
    ]
    host_key = (
        budget.HOST_FAIL_KEY.format(host=name)
        if name and not gnews.is_google_news_url(url)
        else None
    )
    if host_key is not None:
        keys.append(host_key)
    values = await redis.mget(keys)
    summary_cached, teaser_cached, feed_teaser, failed, daily_used, known = values[:6]
    host_failures = values[6] if host_key is not None else None
    if summary_cached is not None or teaser_cached is not None:
        return True
    # Checked only once nothing is cached: the allowlist exists to stop a
    # caller aiming a fetch at an arbitrary URL, and a result we already
    # hold costs nothing to serve.
    if known is None:
        return False
    # The publisher's standfirst from the feed serves even when the article
    # itself is known not to, but only if it survives the junk filter.
    if feed_teaser is not None and clean_teaser(_decoded(feed_teaser)) is not None:
        return True
    if failed is not None:
        return False
    if int(host_failures or 0) >= budget.HOST_FAIL_LIMIT:
        return False
    if gnews.is_google_news_url(url):
        if not settings.GNEWS_RESOLVE_ENABLED:
            return False
        if await gnews.cached_resolution(redis, url) == "":
            return False
    if int(daily_used or 0) >= settings.SUMMARY_DAILY_CAP:
        return False
    # A fresh summary needs a provider that can actually run right now.
    return await build_chains(redis).available(Lane.interactive)


async def warm_summary(
    redis: Redis, url: str, lang: str, origin: str = "viewed"
) -> str:
    """Generate and cache one queued summary on the background lane.
    Returns 'warmed', 'skipped' (already handled or over its own cap),
    'unavailable' (nothing can be warmed right now: the candidate is still
    good, the task requeues it and stops draining) or 'failed' (a
    generation error the task's fuse counts)."""
    chains = build_chains(redis)
    if not await chains.available(Lane.background):
        return "unavailable"
    if lang != "en":
        # Queue entries predating the English-only cut must not spend the
        # warm budget on a language the reader can no longer ask for.
        return "skipped"
    digest = budget.digest(url, lang)
    if await redis.get(budget.CACHE_KEY.format(digest=digest)) is not None:
        return "skipped"
    failed = _decoded(await redis.get(budget.FAIL_KEY.format(digest=digest)))
    if failed is not None and failed != budget.FAIL_HANDOFF:
        return "skipped"
    # Deliberately not gated on the publisher brake: a blackout keeps every
    # live tap off the publisher, so only the warmer, with nobody waiting,
    # ever re-probes it, and one success clears it.
    day = budget.today()
    total_used, warm_used = (
        int(value or 0)
        for value in await redis.mget(
            [budget.DAILY_KEY.format(day=day), budget.WARM_DAILY_KEY.format(day=day)]
        )
    )
    # Three brakes that answer "unavailable", not "skipped": the candidate
    # has already been popped, and nothing more can be warmed this run.
    # Only what readers spent says whether the day is busy enough to leave
    # them the budget; the warmer never walks the total into the global
    # cap either (the last fifth belongs to live taps alone).
    if total_used - warm_used > settings.SUMMARY_DAILY_CAP // 2:
        return "unavailable"
    if total_used >= settings.SUMMARY_DAILY_CAP * 4 // 5:
        return "unavailable"
    if warm_used >= settings.SUMMARY_WARM_DAILY_CAP:
        return "unavailable"
    # Speculative warming gets its own, much smaller allowance.
    if origin == "pretap":
        pretap_used = int(await redis.get(budget.PRETAP_DAILY_KEY.format(day=day)) or 0)
        if pretap_used >= settings.SUMMARY_PRETAP_DAILY_CAP:
            return "skipped"
    try:
        summary = await asyncio.wait_for(
            _produce(redis, url, lang, lane=Lane.background, pretap=origin == "pretap"),
            timeout=WARM_TIMEOUT_SECONDS,
        )
    except ChainExhausted:
        # This minute's free calls belong to live readers, or every free
        # provider is benched: transient, so the candidate goes back.
        return "unavailable"
    except (TimeoutError, *GENERATION_FAILURES) as exc:
        log.info("news.summary_warm_failed", url=url, error=str(exc))
        await budget.mark_failed(redis, url, digest, exc)
        return "failed"
    await budget.mark_succeeded(redis, url, digest, summary)
    return "warmed"
