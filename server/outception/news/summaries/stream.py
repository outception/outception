"""The summary as it is written, for the tap-to-read panel. Same rules as
the whole-result path (cache, teasers, failure memory, single flight,
caps); only a fresh generation actually streams. Events, as plain dicts
for the SSE route:

    {"text": ..., "kind": ...}  a whole result (cache, teaser)
    {"delta": ...}              the next piece of a summary being written
    {"done": True, "kind": ...} the stream finished (text is final)
    {"error": "unavailable"}    nothing to show; open the article
"""

import asyncio
from collections.abc import AsyncGenerator, AsyncIterator

import structlog

from outception.redis import Redis

from ..fetch import NewsFetchError
from . import budget, service
from .errors import LiveDeadlinePassed, SummariesNotConfigured, SummaryUnavailable
from .extract import resolved_article_text
from .prompts import NO_ARTICLE, script_mismatch, scrub_piece, scrub_style
from .providers.lanes import Lane
from .providers.registry import any_configured
from .queue import note_warm_candidate
from .service import (
    GENERATION_FAILURES,
    LIVE_ARTICLE_SECONDS,
    LIVE_FIRST_CHUNK_SECONDS,
    LIVE_STREAM_SECONDS,
    PENDING_KEY,
    PENDING_TTL_SECONDS,
    SummaryResult,
    _acceptable,
    _await_pending,
    _brake,
    _cached_result,
    _teaser_result,
)

log = structlog.get_logger()

# Hold back the first characters: the refusal sentinel must never be
# shown, and the reader should see prose, not a half-word.
NO_ARTICLE_WINDOW = 40


def stream_result(result: SummaryResult) -> dict[str, object]:
    return {"text": result.text, "kind": result.kind}


async def started_in_time(
    stream: AsyncGenerator[str] | AsyncIterator[str], seconds: float, total: float
) -> AsyncIterator[str]:
    """*stream*, with a deadline on its first chunk and a second one on the
    whole thing: a model that has started writing keeps the reader's
    attention, one that has not is given up on before the panel does. The
    total matters as much as the first chunk: the client's timeout applies
    per read, not per stream, so a trickling model had no ceiling at all."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + total
    try:
        try:
            first = await asyncio.wait_for(anext(stream), seconds)
        except StopAsyncIteration:
            return
        except TimeoutError as exc:
            raise LiveDeadlinePassed("model did not start writing in time") from exc
        yield first
        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                raise LiveDeadlinePassed("model did not finish writing in time")
            try:
                chunk = await asyncio.wait_for(anext(stream), remaining)
            except StopAsyncIteration:
                return
            except TimeoutError as exc:
                raise LiveDeadlinePassed(
                    "model did not finish writing in time"
                ) from exc
            yield chunk
    finally:
        aclose = getattr(stream, "aclose", None)
        if aclose is not None:
            await aclose()


async def stream_summary(
    redis: Redis, url: str, lang: str
) -> AsyncIterator[dict[str, object]]:
    if not any_configured():
        raise SummariesNotConfigured()
    if not _acceptable(url):
        yield {"error": "unavailable"}
        return
    digest = budget.digest(url, lang)
    cached = await _cached_result(redis, digest)
    if cached is not None:
        yield stream_result(cached)
        return
    if await redis.get(budget.FAIL_KEY.format(digest=digest)) is not None or (
        await budget.host_blocked(redis, url)
    ):
        result = await _teaser_result(redis, url, digest, None)
        yield (stream_result(result) if result else {"error": "unavailable"})
        return
    pending_key = PENDING_KEY.format(digest=digest)
    if not await redis.set(pending_key, "1", ex=PENDING_TTL_SECONDS, nx=True):
        try:
            result = await _await_pending(redis, digest)
        except SummaryUnavailable:
            yield {"error": "unavailable"}
            return
        yield stream_result(result)
        return
    try:
        async for event in _stream_generate(redis, url, lang, digest):
            yield event
    finally:
        await redis.delete(pending_key)


async def _stream_generate(
    redis: Redis, url: str, lang: str, digest: str
) -> AsyncIterator[dict[str, object]]:
    try:
        braked = await _brake(redis, url, digest)
    except SummaryUnavailable:
        yield {"error": "unavailable"}
        return
    if braked is not None:
        yield stream_result(braked)
        return
    written: list[str] = []
    try:
        try:
            text = await asyncio.wait_for(
                resolved_article_text(redis, url), LIVE_ARTICLE_SECONDS
            )
        except TimeoutError as exc:
            raise LiveDeadlinePassed("article not fetched in time") from exc
        await budget.charge_daily(redis)
        held: str | None = ""
        async for chunk in started_in_time(
            service.stream_text(redis, text, Lane.interactive),
            LIVE_FIRST_CHUNK_SECONDS,
            LIVE_STREAM_SECONDS,
        ):
            if held is not None:
                held += chunk
                if len(held) < NO_ARTICLE_WINDOW:
                    continue
                if NO_ARTICLE in held:
                    raise NewsFetchError("fetched page is not the article")
                piece, held = scrub_piece(held), None
            else:
                piece = scrub_piece(chunk)
            written.append(piece)
            yield {"delta": piece}
        if held:
            if NO_ARTICLE in held:
                raise NewsFetchError("fetched page is not the article")
            piece = scrub_piece(held)
            written.append(piece)
            yield {"delta": piece}
        summary = scrub_style("".join(written))
        if not summary:
            raise NewsFetchError("empty summary")
        if script_mismatch(summary, text):
            raise ValueError("mixed script in summary")
    except GENERATION_FAILURES as exc:
        log.info("news.summary_failed", url=url, error=str(exc))
        await budget.mark_failed(redis, url, digest, exc)
        if isinstance(exc, LiveDeadlinePassed):
            await note_warm_candidate(redis, url, lang, urgent=True)
        if written:
            # Something was already on screen; end the stream rather than
            # swap in a teaser under the reader's eyes.
            yield {"error": "unavailable"}
            return
        result = await _teaser_result(redis, url, digest, exc)
        yield (stream_result(result) if result else {"error": "unavailable"})
        return
    await budget.mark_succeeded(redis, url, digest, summary)
    yield {"done": True, "kind": "summary"}
