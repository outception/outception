"""Public news endpoints powering the landing page.

Unauthenticated by design - the landing page is the logged-out surface.
Heavy lifting is cache-first (Redis); a request only triggers an
outbound fetch when the cached copy aged past the source's interval,
and one broken source never takes down a batch.
"""

import asyncio
import json
import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import structlog
from fastapi import Depends, Header, Query, Request, Response
from fastapi.responses import StreamingResponse

from outception.exceptions import OutceptionError, ResourceNotFound
from outception.kit.http import get_ip_address
from outception.net import state as signal_state
from outception.openapi import APITag
from outception.postgres import (
    AsyncReadSession,
    AsyncSession,
    get_db_read_session,
    get_db_session,
)
from outception.redis import Redis, get_redis
from outception.routing import APIRouter

from . import auth as news_auth
from . import (
    cache,
    client_budget,
    follows,
    heatmap,
    registry,
    search,
    weather,
)
from .briefing.endpoints import router as briefing_router
from .catalog import registry as catalog_registry
from .catalog.decks import default_cards as compose_default_cards
from .catalog.decks import resolve_templates
from .fetch import FETCH_TIMEOUT_SECONDS, StaleFeedError
from .registry import DISABLED_SOURCES
from .schemas import (
    FollowedSources,
    HeatmapResponse,
    NewsItem,
    NewsSearchResponse,
    SourceMeta,
    SourceResponse,
    SummaryAvailability,
    SummaryResponse,
    TemplatesResponse,
    WeatherResponse,
)
from .summaries import queue as summary_queue
from .summaries import service as summaries
from .summaries import stream as summary_stream
from .summaries.errors import SummaryUnavailable

log = structlog.get_logger()

router = APIRouter(prefix="/news", tags=["news"])

# /news/briefing/*: declared before the catch-all source route below.
router.include_router(briefing_router)

# Cap concurrent outbound fetches so a cold-cache batch doesn't open a
# connection per source at once. Sized so the background cache-warmer can
# sweep every source well within its task time limit.
_fetch_semaphore = asyncio.Semaphore(24)

# The roster is static, built once from the catalog, so the registry
# validates and serializes it exactly once: FastAPI's response_model path
# would re-validate and re-serialize every model on every request. The
# strong ETag lets the browser's 5-min revalidations (and the CDN) collapse
# into empty 304s instead of re-downloading the multi-megabyte body.
_catalog = catalog_registry()
_SOURCES_BY_ID: dict[str, SourceMeta] = _catalog.by_id
_SOURCES_BODY: bytes = _catalog.body
_SOURCES_ETAG: str = _catalog.etag


@router.get(
    "/sources",
    response_model=list[SourceMeta],
    response_model_exclude_none=True,
    tags=[APITag.public],
)
async def list_sources(
    request: Request,
    ids: str | None = Query(None, max_length=8192),
) -> Response:
    """Metadata for every known source (including redirect aliases). Pass
    ``ids`` (comma-separated) for just those sources - what the wall needs to
    paint its cards without downloading the multi-megabyte roster."""
    if ids is not None:
        wanted = dict.fromkeys(sid for sid in ids.split(",") if sid)
        subset = [
            meta.model_dump(by_alias=True, exclude_none=True)
            for sid in list(wanted)[:200]
            if (meta := _SOURCES_BY_ID.get(sid)) is not None
        ]
        return Response(
            content=json.dumps(subset, ensure_ascii=False, separators=(",", ":")),
            media_type="application/json",
            headers={
                "Cache-Control": (
                    "public, max-age=300, s-maxage=3600, stale-while-revalidate=86400"
                ),
                "Vary": "Origin",
            },
        )
    # Static content: override the app-wide `private, no-store` default so the
    # browser and any CDN in front of us can serve it without hitting origin.
    # Browsers revalidate after 5 min (so catalog changes reach devices
    # quickly); the CDN keeps its copy for an hour (s-maxage) and shields
    # origin, serving stale while it revalidates. The pre-serialized body
    # skips FastAPI's per-request re-validation of 7k+ models, and the ETag
    # turns those 5-min revalidations into empty 304s.
    headers = {
        "Cache-Control": (
            "public, max-age=300, s-maxage=3600, stale-while-revalidate=86400"
        ),
        # See default_cards: the ACAO header depends on the request Origin.
        "Vary": "Origin",
        "ETag": _SOURCES_ETAG,
    }
    if request.headers.get("if-none-match") == _SOURCES_ETAG:
        return Response(status_code=304, headers=headers)
    return Response(
        content=_SOURCES_BODY, media_type="application/json", headers=headers
    )


@router.get(
    "/sources/{source_id}",
    response_model=SourceMeta,
    response_model_exclude_none=True,
    tags=[APITag.public],
)
async def get_source_meta(source_id: str, response: Response) -> SourceMeta:
    """Metadata for one source - what a share-card unfurl needs, without
    pulling the whole roster."""
    meta = _SOURCES_BY_ID.get(source_id)
    if meta is None:
        raise ResourceNotFound(f"Unknown news source: {source_id}")
    response.headers["Cache-Control"] = (
        "public, max-age=300, s-maxage=3600, stale-while-revalidate=86400"
    )
    response.headers["Vary"] = "Origin"
    return meta


def _ip_country(header: str | None) -> str | None:
    """The edge's two-letter IP country, or None. ``XX`` (unknown), ``T1``
    (Tor) and the regional ``EU``/``AP`` codes are sentinels, not countries -
    left in they'd miss the capitals table and silently yield London weather.

    A client can send this header directly, so treat it as a hint, never as a
    trust signal. That is safe here only because both readers map it through a
    closed set (``_CAPITALS`` / the source roster) and the cards response is
    edge-cacheable (``public``) and therefore sends ``Vary: CF-IPCountry`` -
    note the edge cache ignores Vary, so if edge caching is ever enabled for
    the API, key the cards cache on the ``country`` query param instead."""
    if not header:
        return None
    cc = header.strip().upper()
    return cc if len(cc) == 2 and cc not in {"XX", "T1", "EU", "AP"} else None


@router.get("/default-cards", response_model=list[str], tags=[APITag.public])
# Apps already on readers' phones (1.7.x) still ask for the old path, and a
# store update reaches them slowly, so it keeps answering. Deprecated in the
# schema rather than removed: dropping a published path breaks those clients.
@router.get(
    "/default-deck",
    response_model=list[str],
    tags=[APITag.public],
    deprecated=True,
    # Both paths run the same handler, so the legacy one needs its own id or
    # the generated TypeScript client declares the operation twice.
    operation_id="news:default_deck",
)
async def default_cards(
    response: Response,
    country: str | None = Query(None, min_length=2, max_length=2),
    cf_ipcountry: str | None = Header(None, alias="CF-IPCountry"),
) -> list[str]:
    """The default "Your stack" seeded for a fresh visitor: one representative
    source per major category (world, tech, music, culture, weather, sports,
    science, markets, crypto, betting, gaming). When the reader's ``country``
    is known (the edge's IP country), the generic sports sources are swapped for
    that country's native sports/teams (e.g. Ireland → Gaelic football + hurling,
    USA → NFL/NBA/MLB). Retired sources are dropped."""
    # Anonymous and identical for everyone in a country, so let the edge serve
    # it. MUST Vary on CF-IPCountry (the response depends on it) and on Origin
    # (CORSMatcherMiddleware picks a wildcard or an exact ACAO depending on the
    # request Origin - cache one under the other and CORS breaks).
    response.headers["Cache-Control"] = "public, max-age=600, s-maxage=3600"
    response.headers["Vary"] = "Origin, CF-IPCountry"
    resolved = country or _ip_country(cf_ipcountry)
    cc = resolved.upper() if resolved else None
    return compose_default_cards(_catalog, cc, month=datetime.now(UTC).month)


async def _summarizable(redis: Redis, url: str) -> bool:
    """Whether we will summarize this URL at all. The summary routes take a URL
    from the caller, so without this anyone could aim the article fetcher, the
    day's model budget and the per-host failure brake at any page on the
    internet - three requests are enough to blackout a publisher. Headlines the
    wall has served are remembered by `cache.remember_items`."""
    return await cache.is_known(redis, url)


@router.get(
    "/summary/available",
    response_model=SummaryAvailability,
    tags=[APITag.public],
)
async def get_summary_availability(
    response: Response,
    url: str = Query(..., min_length=12, max_length=2048),
    redis: Redis = Depends(get_redis),
) -> SummaryAvailability:
    """Cheap pre-check for a headline tap: known-unavailable articles (videos,
    paywalls and bot walls seen before, exhausted budget) answer false in a
    few milliseconds so the reader is sent to the article immediately rather
    than after a failed generation."""
    response.headers["Cache-Control"] = "no-store"
    return SummaryAvailability(available=await summaries.is_available(redis, url, "en"))


@router.get("/summary/stream", tags=[APITag.public])
async def stream_article_summary(
    url: str = Query(..., min_length=12, max_length=2048),
    redis: Redis = Depends(get_redis),
) -> StreamingResponse:
    """The summary as server-sent events, so the panel shows the text as it
    is written: `text` (a whole cached or publisher result), `delta` pieces,
    then `done` - or `error` when the reader should open the article."""

    async def events() -> AsyncIterator[str]:
        # Headers are already on the wire once this runs: a failure here must
        # end the stream with an error event, never a severed connection.
        try:
            # Same gate as the non-streaming route: known-markers expire
            # sooner than the summary cache, so checking the allowlist alone
            # bounced readers off summaries that were already written - and
            # /summary/available, which checks the cache first, had just told
            # the client one existed.
            if not (
                await _summarizable(redis, url)
                or await summaries.has_cached(redis, url, "en")
            ):
                yield 'data: {"error": "unavailable"}\n\n'
                return
            async for event in summary_stream.stream_summary(redis, url, "en"):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except OutceptionError as exc:
            yield f'data: {{"error": "{exc.status_code}"}}\n\n'
        except Exception:
            log.exception("news.summary_stream_failed", url=url)
            yield 'data: {"error": "unavailable"}\n\n'

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


@router.get(
    "/summary",
    response_model=SummaryResponse,
    tags=[APITag.public],
    responses={
        502: {"description": "Summary unavailable for this article"},
        503: {"description": "Summaries not configured"},
    },
)
async def get_article_summary(
    response: Response,
    url: str = Query(..., min_length=12, max_length=2048),
    redis: Redis = Depends(get_redis),
) -> SummaryResponse:
    """The summary for a headline tap. One model call per article - everything
    else is served from cache (and the edge can cache it too)."""
    # The allowlist bounds who can aim a fetch and the day's model budget at a
    # URL; a summary already in the cache costs neither. Known-markers expire
    # sooner than the summary cache, so gating on the allowlist alone 502'd
    # readers out of finished summaries.
    if not await _summarizable(redis, url) and not await summaries.has_cached(
        redis, url, "en"
    ):
        raise SummaryUnavailable()
    result = await summaries.get_summary_result(redis, url, "en")
    response.headers["Cache-Control"] = (
        "public, max-age=3600, s-maxage=86400, stale-while-revalidate=604800"
    )
    response.headers["Vary"] = "Origin"
    return SummaryResponse(summary=result.text, url=url, kind=result.kind)


@router.get("/templates", response_model=TemplatesResponse, tags=[APITag.public])
async def get_templates(
    response: Response,
    country: str | None = Query(None, min_length=2, max_length=2),
    cf_ipcountry: str | None = Header(None, alias="CF-IPCountry"),
) -> TemplatesResponse:
    """Starter templates: curated source bundles by persona (developer,
    investor, sports fan, …), country-resolved like the default cards. Display
    names live client-side, keyed by template id."""
    # Same anonymous per-country cacheability as /default-cards.
    response.headers["Cache-Control"] = "public, max-age=600, s-maxage=3600"
    response.headers["Vary"] = "Origin, CF-IPCountry"
    resolved = country or _ip_country(cf_ipcountry)
    cc = resolved.upper() if resolved else None
    return TemplatesResponse.model_validate(
        {"templates": resolve_templates(_catalog, cc)}
    )


@router.get("/weather", response_model=WeatherResponse, tags=[APITag.public])
async def get_weather(
    request: Request,
    response: Response,
    latitude: float | None = Query(None, ge=-90, le=90),
    longitude: float | None = Query(None, ge=-180, le=180),
    country: str | None = Query(None, min_length=2, max_length=2),
    cf_ipcountry: str | None = Header(None, alias="CF-IPCountry"),
    redis: Redis = Depends(get_redis),
) -> WeatherResponse:
    """Current conditions and a short forecast for the reader's location. The
    browser sends precise ``latitude``/``longitude`` when geolocation is
    granted; otherwise it sends the IP ``country`` (from the edge) and we
    resolve that country's capital. Proxied from Open-Meteo, cache-first.

    Native clients have no IP-country cookie to read, so when they send neither
    coordinates nor a country we fall back to the edge's header ourselves -
    otherwise a phone whose UI language is US English would be given US weather
    wherever it actually is."""
    result = await weather.get_weather(
        redis,
        latitude,
        longitude,
        country or _ip_country(cf_ipcountry),
        get_ip_address(request),
    )
    # Cacheable at the edge, like /heatmap. This is anonymous and identical for
    # everyone in a cell: coordinates are already rounded to a ~0.1 degree grid
    # and the entry lives 15 minutes, so readers in the same place share one
    # answer. Without this the app-wide `private, no-store` default made every
    # poll from every reader a full origin hit on a card pinned into EVERY
    # default card set - and origin misses are what spend the global daily cap on
    # the upstream. Vary on CF-IPCountry too: with no coordinates the answer is
    # that country's capital.
    response.headers["Cache-Control"] = (
        "public, max-age=300, s-maxage=900, stale-while-revalidate=3600"
    )
    response.headers["Vary"] = "Origin, CF-IPCountry"
    return WeatherResponse.model_validate(result)


@router.get(
    "/heatmap/{heatmap_id}", response_model=HeatmapResponse, tags=[APITag.public]
)
async def get_heatmap(
    heatmap_id: str,
    response: Response,
    redis: Redis = Depends(get_redis),
) -> HeatmapResponse:
    """Tiles for one market heatmap card (a `type: "heatmap"` roster source).

    Tile area follows `weight` (market cap), color follows `changePercent`.
    Served cache-first with the same success/cache semantics as headline
    sources."""
    result = await heatmap.get_heatmap(redis, heatmap_id)
    # Anonymous and byte-identical for every viewer (the status field is the
    # same for all), so let the edge/browser cache it - without this, every
    # card-seeded heatmap is an origin hit per reader per poll, which is what
    # amplifies concurrent load into a provider-quota stampede. Vary on Origin
    # for the same CORS reason as /default-cards.
    response.headers["Cache-Control"] = (
        "public, max-age=60, s-maxage=300, stale-while-revalidate=3600"
    )
    response.headers["Vary"] = "Origin"
    return HeatmapResponse.model_validate(result)


@router.get("/search", response_model=NewsSearchResponse, tags=[APITag.public])
async def search_news(
    q: str = Query(..., min_length=2, max_length=80, description="Search query."),
    redis: Redis = Depends(get_redis),
) -> NewsSearchResponse:
    """Search the wall: source names (always) and cached headlines (warm
    sources only - search never triggers an outbound fetch)."""
    return NewsSearchResponse(
        sources=search.search_sources(q),
        items=await search.search_headlines(redis, q),
    )


@router.get("/followed", response_model=FollowedSources, tags=[APITag.private])
async def list_followed_sources(
    auth_subject: news_auth.NewsUser,
    session: AsyncReadSession = Depends(get_db_read_session),
) -> FollowedSources:
    """The sources the authenticated user follows (canonical ids)."""
    return FollowedSources(
        source_ids=await follows.list_followed(session, auth_subject.subject.id)
    )


@router.get(
    "/followed/feed",
    response_model=NewsSearchResponse,
    tags=[APITag.private],
)
async def followed_feed(
    auth_subject: news_auth.NewsUser,
    session: AsyncReadSession = Depends(get_db_read_session),
    redis: Redis = Depends(get_redis),
) -> NewsSearchResponse:
    """A merged, freshest-first feed of cached headlines from the sources the
    user follows (warm cache only - never triggers a fetch)."""
    source_ids = await follows.list_followed(session, auth_subject.subject.id)
    return NewsSearchResponse(
        sources=[], items=await follows.followed_feed(redis, source_ids)
    )


@router.put("/followed/{source_id}", status_code=204, tags=[APITag.private])
async def follow_source(
    source_id: str,
    auth_subject: news_auth.NewsUserWrite,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Follow a source. The id is resolved to its canonical source (so a
    redirect alias follows the real one); unknown ids are rejected."""
    resolved = registry.resolve_known(source_id)
    if resolved is None:
        raise ResourceNotFound(f"Unknown news source: {source_id}")
    await follows.follow(session, auth_subject.subject.id, resolved)


@router.delete("/followed/{source_id}", status_code=204, tags=[APITag.private])
async def unfollow_source(
    source_id: str,
    auth_subject: news_auth.NewsUserWrite,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Unfollow a source (idempotent)."""
    resolved = registry.resolve_known(source_id) or source_id
    await follows.unfollow(session, auth_subject.subject.id, resolved)


# A `latest=true` request forces an uncached live fetch. Without a bound, an
# attacker cycling source ids with `latest=true` could turn the API into a
# scraping-DoS amplifier against the 250+ upstreams (and saturate the fetch
# semaphore, stalling the wall for everyone). Gate the forced refresh behind a
# short per-source cooldown so `latest` can't drive back-to-back outbound
# fetches; when it bites, the still-valid cached entry is served instead.
_LATEST_FETCH_COOLDOWN_SECONDS = 30
# Distinct sources one client may force a live refresh of per hour. A reader's
# wall polls the visible card, so real use is a handful; the ceiling only bites
# on a caller cycling ids to hold the shared fetch semaphore.
_CLIENT_HOURLY_LATEST_FETCHES = 120
# Published by a COLD-path leader that gave up (nothing cached, fetch failed or
# timed out), so its followers stop waiting on a cache write that will never
# come. Cleared when a leader starts a fresh cold attempt, and naturally moot
# once anything is cached; scoped to the cooldown, which is exactly how long
# the next attempt is held off anyway.
_COLD_FAIL_KEY = "news:cold-fail:{source}"


async def _note_cold_failure(redis: Redis, source_id: str) -> None:
    """Tell the waiters that this cold fetch is not coming. Only ever called
    with nothing cached - with an entry in hand the leader serves it and there
    is nobody left waiting."""
    await redis.set(
        _COLD_FAIL_KEY.format(source=source_id),
        "1",
        ex=_LATEST_FETCH_COOLDOWN_SECONDS,
    )


# Headlines per card queued for background pre-summarization (see get_source).
# Six, not three: prod showed the warm queue draining faster than cards fed it
# (queue depth ~9 with 750/day of warm budget unspent), while taps below the
# top three still paid the cold ~2s. Deeper is where the returns stop - taps
# past the sixth row are rare, and the warmer skips already-cached entries, so
# the real cost is only the first serve of each fresh headline set.
_WARM_HERO_COUNT = 6

# Viewing a source stamps it into this zset (score = unix time) so the
# background warmer (tasks.warm_demanded_sources) keeps recently-viewed feeds
# warm - without it, a feed nobody opened in 3h expires from the wall cache and
# the next reader pays the full upstream latency (multi-second for the slower
# scrapers) on first paint. 48h covers a daily reader's gap between visits.
# One zset, not a key per source: the per-key form made the warmer SCAN the
# whole keyspace to recover ~40 ids, and it was stamped before the source
# proved viewable, so cycling ids could mark the entire roster demanded and
# stretch the warm rotation from minutes to hours.
SOURCE_DEMAND_KEY = "news:source:demand"
SOURCE_DEMAND_TTL_SECONDS = 48 * 60 * 60


async def _note_source_demand(redis: Redis, source_id: str) -> None:
    await redis.zadd(SOURCE_DEMAND_KEY, {source_id: time.time()})


async def _keep_known(redis: Redis, source_id: str, items: list[NewsItem]) -> None:
    """Keep the headlines we serve in the summary allowlist. Fetching writes it
    (`cache.set`), but a card is served from cache for most of its life and the
    index has to survive a Redis flush, so refresh it on a slow cadence while a
    source is actually being read. One SET NX on the serving path; the write
    itself is a single pipeline, at most once per source per window."""
    if not items:
        return
    if await redis.set(
        cache.KNOWN_REFRESH_KEY.format(id=source_id),
        "1",
        ex=cache.KNOWN_REFRESH_SECONDS,
        nx=True,
    ):
        await cache.remember_items(redis, items, source_id=source_id)


async def _acquire_latest_fetch(
    redis: Redis, source_id: str, client: str | None
) -> bool:
    """Whether this request may force a live refresh of *source_id*.

    Two gates, because the per-source cooldown alone never bound a caller who
    keeps changing source: with 10,000+ registered ids, cycling them never
    re-hits the same cooldown key, so one client could hold all 24 outbound
    fetch slots on 20-second timeouts and stall every reader whose card was
    cold. The per-client allowance bounds how many DISTINCT sources one caller
    may force, which is what the cooldown cannot see."""
    if not await client_budget.spend(
        redis,
        "latest",
        client,
        limit=_CLIENT_HOURLY_LATEST_FETCHES,
        window_seconds=60 * 60,
    ):
        return False
    acquired = await redis.set(
        f"news:latest:cooldown:{source_id}",
        "1",
        ex=_LATEST_FETCH_COOLDOWN_SECONDS,
        nx=True,
    )
    return bool(acquired)


async def _get_source(
    redis: Redis, source_id: str, *, latest: bool, client: str | None = None
) -> SourceResponse:
    resolved = registry.resolve(source_id)
    if resolved is None or resolved in DISABLED_SOURCES:
        # Disabled sources are hidden from the roster, but nothing stopped a
        # crafted id from driving live fetches at upstreams we already know are
        # dead or blocking us - a free scraping amplifier.
        raise ResourceNotFound(f"Unknown news source: {source_id}")

    now = cache.now_ms()
    entry = await cache.get(redis, resolved)
    if entry is not None:
        # Demand is only stamped once the source has proven viewable (cache
        # content in hand, or a successful fetch below) - stamping on entry
        # let anyone cycling ids hijack the warmer's whole rotation.
        await _note_source_demand(redis, resolved)
        # Fresher than the source's own update cadence: serve as-is.
        if now - entry.updated < registry.interval_ms(resolved):
            await _keep_known(redis, resolved, entry.items)
            return SourceResponse(
                status="success",
                id=resolved,
                updated_time=entry.updated,
                items=entry.items,
            )
        # Stale but within the hard TTL: serve marked as cache, unless the
        # client explicitly asked for the latest AND a live refresh for this
        # source isn't on cooldown. `_acquire_latest_fetch` is only evaluated
        # when `latest` is set (short-circuit), so normal reads are unaffected
        # and never consume the cooldown.
        if now - entry.updated < cache.TTL_MS and not (
            latest and await _acquire_latest_fetch(redis, resolved, client)
        ):
            await _keep_known(redis, resolved, entry.items)
            return SourceResponse(
                status="cache",
                id=resolved,
                updated_time=entry.updated,
                items=entry.items,
            )

    if entry is None and not await _acquire_latest_fetch(redis, resolved, client):
        # Nothing cached and another live fetch for this source ran within the
        # cooldown (in flight right now, or it just failed). Without taking the
        # cooldown on the cold path, cycling ids across the roster drove one
        # outbound fetch per request - the cheapest scraping amplifier the API
        # had. Followers briefly wait on the leader's cache write instead of
        # 502ing: after a cold start every reader but the first otherwise saw
        # the card's error state for the whole 30s cooldown.
        # Immediate first check (the leader may already have written), then
        # backing off - a dead source's followers cost 6 reads over ~6s, not
        # 20 at a fixed cadence. The ladder is only ever ridden to the end
        # while the leader is STILL fetching, which is productive waiting: a
        # leader that already gave up publishes the marker below and its
        # followers fail with it, instead of each holding a request open for
        # six seconds to re-discover the same dead upstream.
        for pause in (0, 0.3, 0.5, 0.8, 1.2, 1.6, 1.6):
            if pause:
                await asyncio.sleep(pause)
            if await redis.get(_COLD_FAIL_KEY.format(source=resolved)) is not None:
                break
            entry = await cache.get(redis, resolved)
            if entry is not None:
                await _note_source_demand(redis, resolved)
                await _keep_known(redis, resolved, entry.items)
                return SourceResponse(
                    status="cache",
                    id=resolved,
                    updated_time=entry.updated,
                    items=entry.items,
                )
        raise OutceptionError(f"News source unavailable: {resolved}", status_code=502)

    if entry is None:
        # A fresh cold attempt is starting: retire the previous leader's
        # failure marker so THIS fetch is what its followers wait on.
        await redis.delete(_COLD_FAIL_KEY.format(source=resolved))

    try:
        async with _fetch_semaphore:
            getter = registry.GETTERS[resolved]
            # The client's own 10s timeout is per operation, not per fetch, and
            # the transport retries twice - so a drip-feeding upstream can hold
            # one of the 24 shared slots far longer than it looks. The worker
            # learned this in prod and got its own bound; the request path,
            # where a held slot stalls the wall for everyone, never did.
            items = (await asyncio.wait_for(getter(), FETCH_TIMEOUT_SECONDS))[:30]
        # An empty result still has to advance the cache stamp - skipping the
        # write leaves `updated` stale forever, so every poll sees an expired
        # card and refetches the dead upstream for as long as a tab is open.
        # But don't let a momentary empty (upstream mid-deploy, a selector that
        # matched nothing without raising) throw away good headlines: re-stamp
        # the last known good set instead.
        if not items and entry is not None and entry.items:
            # Carry the last good set through a momentary empty - but not
            # forever: cache.set re-stamps `updated`, so entry age can never
            # exceed one TTL and an age check is a tautology. The marker
            # below survives the re-stamps: it is set on the FIRST empty
            # fetch and cleared by any non-empty one, so a scraper whose
            # markup changed stops serving week-old headlines as fresh once
            # the marker outlives the cache TTL.
            empty_key = f"news:empty-since:{resolved}"
            empty_since = await redis.get(empty_key)
            if empty_since is None:
                await redis.set(empty_key, str(now), ex=2 * cache.TTL_MS // 1000)
                items = entry.items
            elif now - int(empty_since) < cache.TTL_MS:
                items = entry.items
        elif items:
            await redis.delete(f"news:empty-since:{resolved}")
        updated = await cache.set(redis, resolved, items)
        await _note_source_demand(redis, resolved)
        await signal_state.clear_failure(redis, resolved)
        return SourceResponse(
            status="success", id=resolved, updated_time=updated, items=items
        )
    except TimeoutError as exc:
        # Caught before the generic handler for two reasons: `str(TimeoutError())`
        # is empty, so it would log an unreadable failure; and taking the refetch
        # cooldown stops a source that times out every time from spending one of
        # the shared fetch slots on every poll for as long as a tab is open.
        log.info("news.fetch_timeout", source=resolved, seconds=FETCH_TIMEOUT_SECONDS)
        await _acquire_latest_fetch(redis, resolved, client)
        await signal_state.note_failure(redis, resolved, "timeout")
        if entry is not None:
            await _keep_known(redis, resolved, entry.items)
            return SourceResponse(
                status="cache",
                id=resolved,
                updated_time=entry.updated,
                items=entry.items,
            )
        await _note_cold_failure(redis, resolved)
        raise OutceptionError(
            f"News source unavailable: {resolved}", status_code=502
        ) from exc
    except StaleFeedError as exc:
        # The upstream is abandoned, so the cached copy is exactly as old. Cache
        # the emptiness - the card reads "no headlines" instead of presenting
        # years-old stories as news, and the source still recovers by itself if
        # the publisher ever starts posting again.
        log.info("news.feed_abandoned", source=resolved, error=str(exc))
        await signal_state.note_failure(redis, resolved, "stale_feed")
        updated = await cache.set(redis, resolved, [])
        return SourceResponse(
            status="success", id=resolved, updated_time=updated, items=[]
        )
    except Exception as exc:  # scrapers parse wild HTML - anything can raise
        log.info("news.fetch_failed", source=resolved, error=str(exc))
        await signal_state.note_failure(redis, resolved, type(exc).__name__)
        if entry is not None:
            await _keep_known(redis, resolved, entry.items)
            return SourceResponse(
                status="cache",
                id=resolved,
                updated_time=entry.updated,
                items=entry.items,
            )
        await _note_cold_failure(redis, resolved)
        raise OutceptionError(
            f"News source unavailable: {resolved}", status_code=502
        ) from exc


@router.get("/{source_id}", response_model=SourceResponse, tags=[APITag.public])
async def get_source(
    request: Request,
    source_id: str,
    latest: bool = Query(False),
    redis: Redis = Depends(get_redis),
) -> SourceResponse:
    """Items for one source - cache-first with the ported TTL semantics."""
    response = await _get_source(
        redis, source_id, latest=latest, client=get_ip_address(request)
    )
    if response.items:
        # Readers tap the top of a card far more than its tail, but "the hero
        # only" left every other tap paying the full cold cost (~9s: article
        # fetch plus a model call). Queue the top few so most taps land on a
        # cache hit; the warmer is free-tier only, daily-capped, and skips
        # anything already cached, so the extra candidates cost nothing once
        # they are warm.
        #
        # One batched call, not one per hero: this is the hottest read path,
        # and per-URL queueing cost two Redis round trips EACH (twelve per
        # serve) where the batch costs two total.
        await summary_queue.note_warm_candidates(
            redis,
            [item.url for item in response.items[:_WARM_HERO_COUNT] if item.url],
            "en",
        )
    return response
