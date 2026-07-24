"""Public news endpoints powering the landing page.

Unauthenticated by design — the landing page is the logged-out surface.
Heavy lifting is cache-first (Redis); a request only triggers an
outbound fetch when the cached copy aged past the source's interval,
and one broken source never takes down a batch.
"""

import asyncio

import structlog
from fastapi import Depends, Query

from outception.exceptions import OutceptionError, ResourceNotFound
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
from . import cache, follows, registry, search, translate, weather
from .metadata import SOURCES, SourceInfo
from .schemas import (
    BatchRequest,
    FollowedSources,
    NewsSearchItem,
    NewsSearchResponse,
    SourceMeta,
    SourceResponse,
    TranslateRequest,
    TranslateResponse,
    WeatherResponse,
)

log = structlog.get_logger()

router = APIRouter(prefix="/news", tags=["news"])

# Default deck order: lead with mainstream/global news and sports the way a
# news front page does, and push tech/social/niche columns lower. Sources keep
# their registration order within a column (stable sort).
_COLUMN_ORDER = {
    "news": 0,
    "world": 1,
    "sports": 2,
    "finance": 3,
    "science": 4,
    "entertainment": 5,
    "tech": 6,
    "social": 7,
    "betting": 8,
}


# Sources confirmed to consistently fail (dead feeds, paywalls, or upstreams
# that block/timeout this server). Hidden from the wall so no broken cards show.
DISABLED_SOURCES: frozenset[str] = frozenset(
    {
        "9news_au",
        "9to5linux",
        "actucameroun",
        "arabnews",
        "bangkokpost",
        "bostonglobe",
        "cbssports",
        "cnbc",
        "destructoid",
        "dotesports",
        "fin24",
        "fxstreet",
        "gothamist",
        "greekreporter",
        "guardianng",
        "herald_zw",
        "houstonchronicle",
        "hypebeast",
        "jamaicaobserver",
        "japantoday",
        "jeuneafrique",
        "kotaku",
        "mailguardian",
        "mg_africa",
        "news24_za2",
        "newscientist",
        "peruviantimes",
        "politico",
        "rte_ie",
        "seattletimes",
        "seattletimes2",
        "siliconera",
        "sportskeeda",
        "stuttgarter",
        "terra_br",
        "theatlantic",
        "thedefiant",
        "theinformation",
        "timesofisrael",
        "tmz",
        "tvn24",
        "udn",
        "ukroads",
        "youtube-lalalifegames",
    }
)


def _ordered_sources() -> list[tuple[str, SourceInfo]]:
    return sorted(
        ((sid, meta) for sid, meta in SOURCES.items() if sid not in DISABLED_SOURCES),
        key=lambda kv: _COLUMN_ORDER.get(kv[1].get("column", ""), len(_COLUMN_ORDER)),
    )


# Cap concurrent outbound fetches so a cold-cache batch doesn't open a
# connection per source at once. Sized so the background cache-warmer can
# sweep every source well within its task time limit.
_fetch_semaphore = asyncio.Semaphore(24)


@router.get("/sources", response_model=list[SourceMeta], tags=[APITag.public])
async def list_sources() -> list[SourceMeta]:
    """Metadata for every known source (including redirect aliases)."""
    return [
        SourceMeta.model_validate(
            {
                "id": source_id,
                "interval": meta.get("interval", cache.DEFAULT_INTERVAL_MS),
                **{
                    k: v
                    for k, v in meta.items()
                    if k
                    in (
                        "name",
                        "color",
                        "column",
                        "type",
                        "home",
                        "title",
                        "desc",
                        "redirect",
                    )
                },
            }
        )
        for source_id, meta in _ordered_sources()
    ]


# The default "Your deck" for every reader, regardless of location or
# language: a curated spread of major categories in reading order, roughly
# three text sources per category plus a matching YouTube channel where a good
# one exists. A fresh visitor opens onto this spread and then follows/unfollows
# to curate. The weather card isn't a scraped source (no getter, no metadata
# row): it's a synthetic deck entry the frontend renders from the /news/weather
# proxy, and the wall pins it to the end regardless of its position here.
WEATHER_DECK_ID = "weather"

DEFAULT_DECK: tuple[str, ...] = (
    # World news
    "bbc-world",
    "nytimes",
    "wsj",
    "foxnews",
    "youtube-reuters",
    # Politics
    "thehill",
    "nprpolitics",
    "realclearpolitics",
    "youtube-thehill",
    # Science
    "sciencedaily",
    "nytscience",
    "nprscience",
    "youtube-veritasium",
    # Health
    "nythealth",
    "nprhealth",
    "menshealth",
    "youtube-hubermanlab",
    # Climate & environment (no mainstream YouTube channel available)
    "carbonbrief",
    "grist",
    "guardianenvironment",
    # Business (tech & startups)
    "producthunt",
    "hackernews",
    "techcrunch",
    "youtube-techcrunch",
    # Tech & gadgets
    "theverge",
    "engadget",
    "arstechnica",
    "youtube-mkbhd",
    # AI
    "openai",
    "deepmind",
    "venturebeat",
    "youtube-twominutepapers",
    # Stocks & crypto
    "marketwatch",
    "coindesk",
    "cointelegraph",
    "youtube-bloombergbiz",
    # Culture & movies
    "variety",
    "hollywoodreporter",
    "deadline",
    "youtube-rottentomatoestrailers",
    # Music
    "pitchfork",
    "billboard",
    "rollingstone",
    "youtube-taylorswift",
    # Food & cooking
    "bonappetit",
    "eater",
    "fooddive",
    "youtube-joshuaweissman",
    # Gaming
    "ign",
    "gamespot",
    "eurogamer",
    "youtube-videogamedunkey",
    # Sport
    "bbcsport",
    "guardiansport",
    "skysports",
    "youtube-espn",
    # Betting (no mainstream YouTube channel available)
    "legalsportsreport",
    "sbcnews",
    "vsin",
    # Weather (synthetic — see WEATHER_DECK_ID; frontend pins it last)
    WEATHER_DECK_ID,
)


@router.get("/default-deck", response_model=list[str], tags=[APITag.public])
async def default_deck() -> list[str]:
    """The default "Your deck" seeded for a fresh visitor: one representative
    source per major category (world, tech, music, culture, weather, sports,
    science, markets, crypto, betting, gaming) — the same for every reader
    regardless of location or language. Retired sources are dropped."""
    return [
        sid
        for sid in DEFAULT_DECK
        if sid == WEATHER_DECK_ID or (sid in SOURCES and sid not in DISABLED_SOURCES)
    ]


@router.get("/weather", response_model=WeatherResponse, tags=[APITag.public])
async def get_weather(
    latitude: float | None = Query(None, ge=-90, le=90),
    longitude: float | None = Query(None, ge=-180, le=180),
    country: str | None = Query(None, min_length=2, max_length=2),
    redis: Redis = Depends(get_redis),
) -> WeatherResponse:
    """Current conditions and a short forecast for the reader's location. The
    browser sends precise ``latitude``/``longitude`` when geolocation is
    granted; otherwise it sends the IP ``country`` (from Cloudflare) and we
    resolve that country's capital. Proxied from Open-Meteo, cache-first."""
    result = await weather.get_weather(redis, latitude, longitude, country)
    return WeatherResponse.model_validate(result)


@router.post("/translate", response_model=TranslateResponse, tags=[APITag.public])
async def translate_headlines(
    body: TranslateRequest,
    redis: Redis = Depends(get_redis),
) -> TranslateResponse:
    """Machine-translate a batch of headlines into the reader's language,
    cache-first. Translating into English is a no-op (sources are already mostly
    English) — the texts are returned unchanged."""
    if body.target == "en":
        return TranslateResponse(translations=body.texts)
    translations = await translate.translate_texts(redis, body.texts, body.target)
    return TranslateResponse(translations=translations)


@router.get("/search", response_model=NewsSearchResponse, tags=[APITag.public])
async def search_news(
    q: str = Query(..., min_length=2, max_length=80, description="Search query."),
    lang: str | None = Query(
        None,
        min_length=2,
        max_length=8,
        description="Translate result headlines into this language.",
    ),
    redis: Redis = Depends(get_redis),
) -> NewsSearchResponse:
    """Search the wall: source names (always) and cached headlines (warm
    sources only — search never triggers an outbound fetch). Result headlines
    are translated into ``lang`` when set, like the source cards."""
    items = await search.search_headlines(redis, q)
    return NewsSearchResponse(
        sources=search.search_sources(q),
        items=await _translate_hits(redis, items, lang),
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
    lang: str | None = Query(
        None,
        min_length=2,
        max_length=8,
        description="Translate feed headlines into this language.",
    ),
    redis: Redis = Depends(get_redis),
) -> NewsSearchResponse:
    """A merged, freshest-first feed of cached headlines from the sources the
    user follows (warm cache only — never triggers a fetch). Headlines are
    translated into ``lang`` when set, like the source cards."""
    source_ids = await follows.list_followed(session, auth_subject.subject.id)
    items = await follows.followed_feed(redis, source_ids)
    return NewsSearchResponse(
        sources=[], items=await _translate_hits(redis, items, lang)
    )


@router.put("/followed/{source_id}", status_code=204, tags=[APITag.private])
async def follow_source(
    source_id: str,
    auth_subject: news_auth.NewsUser,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Follow a source. The id is resolved to its canonical source (so a
    redirect alias follows the real one); unknown ids are rejected."""
    resolved = registry.resolve(source_id)
    if resolved is None:
        raise ResourceNotFound(f"Unknown news source: {source_id}")
    await follows.follow(session, auth_subject.subject.id, resolved)


@router.delete("/followed/{source_id}", status_code=204, tags=[APITag.private])
async def unfollow_source(
    source_id: str,
    auth_subject: news_auth.NewsUser,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    """Unfollow a source (idempotent)."""
    resolved = registry.resolve(source_id) or source_id
    await follows.unfollow(session, auth_subject.subject.id, resolved)


# A `latest=true` request forces an uncached live fetch. Without a bound, an
# attacker cycling source ids with `latest=true` could turn the API into a
# scraping-DoS amplifier against the 250+ upstreams (and saturate the fetch
# semaphore, stalling the wall for everyone). Gate the forced refresh behind a
# short per-source cooldown so `latest` can't drive back-to-back outbound
# fetches; when it bites, the still-valid cached entry is served instead.
_LATEST_FETCH_COOLDOWN_SECONDS = 30


async def _acquire_latest_fetch(redis: Redis, source_id: str) -> bool:
    acquired = await redis.set(
        f"news:latest:cooldown:{source_id}",
        "1",
        ex=_LATEST_FETCH_COOLDOWN_SECONDS,
        nx=True,
    )
    return bool(acquired)


async def _get_source(redis: Redis, source_id: str, *, latest: bool) -> SourceResponse:
    resolved = registry.resolve(source_id)
    if resolved is None:
        raise ResourceNotFound(f"Unknown news source: {source_id}")

    now = cache.now_ms()
    entry = await cache.get(redis, resolved)
    if entry is not None:
        # Fresher than the source's own update cadence: serve as-is.
        if now - entry.updated < registry.interval_ms(resolved):
            return SourceResponse(
                status="success", id=resolved, updated_time=now, items=entry.items
            )
        # Stale but within the hard TTL: serve marked as cache, unless the
        # client explicitly asked for the latest AND a live refresh for this
        # source isn't on cooldown. `_acquire_latest_fetch` is only evaluated
        # when `latest` is set (short-circuit), so normal reads are unaffected
        # and never consume the cooldown.
        if now - entry.updated < cache.TTL_MS and not (
            latest and await _acquire_latest_fetch(redis, resolved)
        ):
            return SourceResponse(
                status="cache",
                id=resolved,
                updated_time=entry.updated,
                items=entry.items,
            )

    try:
        async with _fetch_semaphore:
            getter = registry.GETTERS[resolved]
            items = (await getter())[:30]
        if items:
            await cache.set(redis, resolved, items)
        return SourceResponse(
            status="success", id=resolved, updated_time=now, items=items
        )
    except Exception as exc:  # scrapers parse wild HTML — anything can raise
        log.info("news.fetch_failed", source=resolved, error=str(exc))
        if entry is not None:
            return SourceResponse(
                status="cache",
                id=resolved,
                updated_time=entry.updated,
                items=entry.items,
            )
        raise OutceptionError(
            f"News source unavailable: {resolved}", status_code=502
        ) from exc


@router.get("/{source_id}", response_model=SourceResponse, tags=[APITag.public])
async def get_source(
    source_id: str,
    latest: bool = Query(False),
    lang: str | None = Query(
        None,
        min_length=2,
        max_length=8,
        description="Translate headlines into this language (cache-first).",
    ),
    redis: Redis = Depends(get_redis),
) -> SourceResponse:
    """Items for one source — cache-first with the ported TTL semantics. When
    ``lang`` is set the headlines are machine-translated into it before the
    response returns, so the card renders in the reader's language on first
    paint (no English flash, no second round trip). This runs for English
    readers too: the translator auto-detects the source language, so a foreign
    source (e.g. a Croatian or French outlet) is rendered in English for an
    English reader, while an already-English source detects en→en and is
    returned unchanged (and cached), so there's no wasted work after the first
    fetch of each headline."""
    response = await _get_source(redis, source_id, latest=latest)
    if lang and response.items:
        titles = await translate.translate_texts(
            redis, [item.title for item in response.items], lang
        )
        response.items = [
            item.model_copy(update={"title": title})
            for item, title in zip(response.items, titles)
        ]
    return response


async def _translate_hits(
    redis: Redis, hits: list[NewsSearchItem], lang: str | None
) -> list[NewsSearchItem]:
    """Machine-translate the headline titles of search/feed hits into *lang*
    (cache-first), returning them unchanged when *lang* is unset. Mirrors the
    per-source card translation so followed-feed and search results also render
    in the reader's language (incl. English readers reading a foreign source)."""
    if not (lang and hits):
        return hits
    titles = await translate.translate_texts(
        redis, [hit.item.title for hit in hits], lang
    )
    return [
        hit.model_copy(update={"item": hit.item.model_copy(update={"title": title})})
        for hit, title in zip(hits, titles)
    ]


@router.post("/batch", response_model=list[SourceResponse], tags=[APITag.public])
async def batch(
    body: BatchRequest,
    redis: Redis = Depends(get_redis),
) -> list[SourceResponse]:
    """Cached items for many sources in one round trip (upstream
    `entire` semantics): NEVER triggers outbound fetches — cold or
    unknown sources are simply absent from the response, and each card
    lazy-fetches its own source as it scrolls into view. This is what
    makes a warm wall render instantly."""

    async def cached(source_id: str) -> SourceResponse | None:
        resolved = registry.resolve(source_id)
        if resolved is None:
            return None
        entry = await cache.get(redis, resolved)
        if entry is None:
            return None
        fresh = cache.now_ms() - entry.updated < registry.interval_ms(resolved)
        return SourceResponse(
            status="success" if fresh else "cache",
            id=resolved,
            updated_time=entry.updated,
            items=entry.items,
        )

    results = await asyncio.gather(*(cached(s) for s in body.sources))
    return [r for r in results if r is not None]
