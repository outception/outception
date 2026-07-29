"""Public news endpoints powering the landing page.

Unauthenticated by design - the landing page is the logged-out surface.
Heavy lifting is cache-first (Redis); a request only triggers an
outbound fetch when the cached copy aged past the source's interval,
and one broken source never takes down a batch.
"""

import asyncio
import hashlib
import json
import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import structlog
from fastapi import Depends, Header, Query, Request, Response
from fastapi.responses import StreamingResponse

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
from . import (
    cache,
    follows,
    games,
    heatmap,
    registry,
    search,
    summary,
    translate,
    weather,
)
from .cities_data import COUNTRY_TOP_CITY
from .fetch import FETCH_TIMEOUT_SECONDS, StaleFeedError
from .metadata import SOURCES, SourceInfo
from .registry import DISABLED_SOURCES
from .schemas import (
    BatchRequest,
    CrosswordResponse,
    FollowedSources,
    HeatmapResponse,
    NewsItem,
    NewsSearchItem,
    NewsSearchResponse,
    SourceMeta,
    SourceResponse,
    SummaryAvailability,
    SummaryResponse,
    TemplatesResponse,
    TranslateRequest,
    TranslateResponse,
    WeatherResponse,
)
from .shopping_data import (
    COUNTRY_BUSINESS,
    COUNTRY_DEALS,
    COUNTRY_EVENTS,
    COUNTRY_HEALTH,
    COUNTRY_PROPERTY,
    COUNTRY_TRAVEL,
)
from .teams_data import COUNTRY_SPORTS

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


def _ordered_sources() -> list[tuple[str, SourceInfo]]:
    return sorted(
        ((sid, meta) for sid, meta in SOURCES.items() if sid not in DISABLED_SOURCES),
        key=lambda kv: _COLUMN_ORDER.get(kv[1].get("column", ""), len(_COLUMN_ORDER)),
    )


# Cap concurrent outbound fetches so a cold-cache batch doesn't open a
# connection per source at once. Sized so the background cache-warmer can
# sweep every source well within its task time limit.
_fetch_semaphore = asyncio.Semaphore(24)


# The roster is static - built at import time from the source registry - so
# validate it once instead of re-running ~1500 model validations per request on
# the wall's first-paint path.
def _build_sources_payload() -> list[SourceMeta]:
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
                        "logo",
                    )
                },
            }
        )
        for source_id, meta in _ordered_sources()
    ]


_SOURCES_PAYLOAD: list[SourceMeta] = _build_sources_payload()

# The roster is immutable per process, so serialize it exactly once: FastAPI's
# response_model path re-validates and re-serializes all 5,700+ models on every
# request (~9 ms of event-loop CPU). The strong ETag lets the browser's 5-min
# revalidations (and Cloudflare) collapse into empty 304s instead of 1.3 MB
# re-downloads.
_SOURCES_BODY: bytes = json.dumps(
    [m.model_dump(by_alias=True, exclude_none=True) for m in _SOURCES_PAYLOAD],
    ensure_ascii=False,
    separators=(",", ":"),
).encode()
_SOURCES_ETAG: str = f'"{hashlib.md5(_SOURCES_BODY).hexdigest()[:20]}"'


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
    paint its deck without downloading the multi-megabyte roster."""
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
        # See default_deck: the ACAO header depends on the request Origin.
        "Vary": "Origin",
        "ETag": _SOURCES_ETAG,
    }
    if request.headers.get("if-none-match") == _SOURCES_ETAG:
        return Response(status_code=304, headers=headers)
    return Response(
        content=_SOURCES_BODY, media_type="application/json", headers=headers
    )


_SOURCES_BY_ID: dict[str, SourceMeta] = {meta.id: meta for meta in _SOURCES_PAYLOAD}


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


# The default "Your deck" for every reader, regardless of location or
# language: a curated spread of major categories in reading order, roughly
# three text sources per category plus a matching YouTube channel where a good
# one exists. A fresh visitor opens onto this spread and then follows/unfollows
# to curate. The weather card isn't a scraped source (no getter, no metadata
# row): it's a synthetic deck entry the frontend renders from the /news/weather
# proxy, and the wall pins it to the end regardless of its position here.
WEATHER_DECK_ID = "weather"

# One representative card per category - the wall now spans far more categories
# (lifestyle, food, travel, culture, faith, …), so the seed is a single strong
# source each rather than 3-4, keeping the fresh-visitor deck broad but light.
DEFAULT_DECK: tuple[str, ...] = (
    # Text and video companions come from DIFFERENT brands on purpose - every
    # pair widens the source variety instead of doubling one outlet.
    "bbc-world",  # World news
    "youtube-guardian",  # …and Guardian News on video
    "thehill",  # Politics
    "propublica",  # …and investigative bombshells
    "marketwatch",  # Business & markets
    "heatmap-tech",  # …and the tech-stocks heatmap card
    "coindesk",  # Crypto
    "heatmap-crypto",  # …and the crypto heatmap card
    # Data & charts - the "interesting statistics" beat: chart-led stories
    # closing out the numbers block before the deck turns to health/tech.
    # Visual Capitalist rather than OWID/FRED: broadest of the three chart
    # sources (those stay one search away in the roster).
    "visualcapitalist",  # Charts & data
    # The science/bombshell block rides beside the politics pair (see
    # inject_after); every deck card covers a DISTINCT beat - no two cards
    # carry the same stories.
    "nythealth",  # Health
    "theverge",  # Tech
    "youtube-mkbhd",  # …and tech video from a different brand (MKBHD)
    "openai",  # AI
    "variety",  # Entertainment
    "youtube-mrbeast",  # Entertainment video (MrBeast)
    "movie-new",  # Movies
    "tv-new",  # TV
    "anime-new",  # Anime
    "music-new",  # Music
    "game-new",  # Gaming
    "book-new",  # Books
    "tech-new",  # Gadgets
    "car-new",  # Cars
    "youtube-carwow",  # Cars video (carwow)
    "podcast-new",  # Podcasts
    "life-recipes",  # Food
    "youtube-markwiens",  # Food video (Mark Wiens)
    "life-budgettravel",  # Travel
    "youtube-yestheory",  # Travel video (Yes Theory)
    "life-fashion",  # Lifestyle
    "life-history",  # Culture
    "youtube-vox",  # Culture video (Vox)
    "quotes",  # Quote of the day
    "life-lifehacks",  # Social
    "bbcsport",  # Sport (swapped for the visitor country's sports)
    "heatmap-ucl",  # …and the Champions League heat grid
    "legalsportsreport",  # Betting
    WEATHER_DECK_ID,  # Weather (synthetic - frontend pins it last)
)

# Playable breaks, spaced at the quarter marks of the FINAL assembled deck
# (after localisation and injection): crossword after the first quarter,
# sudoku at the half, solitaire after the third quarter, the cube closing.
_GAME_BREAKS: tuple[str, ...] = ("crossword", "sudoku", "solitaire")


# The generic sports sources in DEFAULT_DECK, swapped for the visitor country's
# native sports when we know their country (see COUNTRY_SPORTS).
_ENGLISH_DECK: frozenset[str] = frozenset(
    {"US", "GB", "IE", "CA", "AU", "NZ", "ZA", "SG", "IN", "PH", "MY", "NG", "KE"}
)

_GENERIC_SPORTS: frozenset[str] = frozenset(
    {"bbcsport", "guardiansport", "skysports", "youtube-espn"}
)

# The deck's sports heat grid localises like the sports sources do: the generic
# Champions League grid is swapped for the visitor country's biggest
# competition (cricket in India, NFL in the US, …).
# Key-gated maps that aren't configured fall out in the response filter below,
# exactly like any other unavailable source. Unmapped countries keep UCL.
# The biggest podcast we carry per IP country; TED Talks Daily is the global
# fallback so every fresh deck opens with one podcast card.
COUNTRY_PODCAST: dict[str, str] = {
    "US": "podcast-thejoeroganexperience",
    "CA": "podcast-thejoeroganexperience",
    "AU": "podcast-thejoeroganexperience",
    "NZ": "podcast-thejoeroganexperience",
    "GB": "podcast-thediaryofaceo",
    "IE": "podcast-thediaryofaceo",
    "IN": "podcast-onpurposejayshetty",
}
DEFAULT_PODCAST = "podcast-tedtalksdaily"

COUNTRY_SPORT_HEATMAPS: dict[str, tuple[str, ...]] = {
    "US": ("heatmap-nfl", "heatmap-nba"),
    "CA": ("heatmap-nhl",),
    "MX": ("heatmap-liga-mx",),
    "GB": ("heatmap-premier-league",),
    "IE": ("heatmap-premier-league",),
    "ES": ("heatmap-la-liga",),
    "DE": ("heatmap-bundesliga",),
    "AT": ("heatmap-bundesliga",),
    "CH": ("heatmap-bundesliga",),
    "IT": ("heatmap-serie-a",),
    "FR": ("heatmap-ligue-1", "heatmap-top14"),
    "NL": ("heatmap-eredivisie",),
    "PT": ("heatmap-primeira-liga",),
    "BR": ("heatmap-brasileirao",),
    "IN": ("heatmap-cricket",),
    "PK": ("heatmap-cricket",),
    "BD": ("heatmap-cricket",),
    "LK": ("heatmap-cricket",),
    "AU": ("heatmap-cricket",),
    "NZ": ("heatmap-cricket",),
    "ZA": ("heatmap-urc", "heatmap-cricket"),
    "JP": ("heatmap-mlb",),
    "KR": ("heatmap-mlb",),
}


def _ip_country(header: str | None) -> str | None:
    """Cloudflare's two-letter IP country, or None. ``XX`` (unknown), ``T1``
    (Tor) and the regional ``EU``/``AP`` codes are sentinels, not countries -
    left in they'd miss the capitals table and silently yield London weather.

    A client can send this header directly, so treat it as a hint, never as a
    trust signal. That is safe here only because both readers map it through a
    closed set (``_CAPITALS`` / the source roster) and the deck response is
    edge-cacheable (``public``) and therefore sends ``Vary: CF-IPCountry`` -
    note Cloudflare ignores Vary, so if CF edge caching is ever enabled for
    the API, key the deck cache on the ``country`` query param instead."""
    if not header:
        return None
    cc = header.strip().upper()
    return cc if len(cc) == 2 and cc not in {"XX", "T1", "EU", "AP"} else None


@router.get("/default-deck", response_model=list[str], tags=[APITag.public])
async def default_deck(
    response: Response,
    country: str | None = Query(None, min_length=2, max_length=2),
    cf_ipcountry: str | None = Header(None, alias="CF-IPCountry"),
) -> list[str]:
    """The default "Your deck" seeded for a fresh visitor: one representative
    source per major category (world, tech, music, culture, weather, sports,
    science, markets, crypto, betting, gaming). When the reader's ``country``
    is known (Cloudflare IP country), the generic sports sources are swapped for
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
    country_sports = COUNTRY_SPORTS.get(cc) if cc else None
    deck: list[str] = []
    # First-session narrative: relevance (your country's news), then a trust
    # anchor (BBC World), then the second personalisation beat (your city),
    # then the big podcast card. The category spread follows, with each
    # localized vertical injected right after its category's brand anchor
    # (their country's source, else nothing - never generic), and each
    # heatmap sitting beside its related news card (crypto map after CoinDesk,
    # sport tables after the sports sources).
    if cc:
        news_id = f"gnews-{cc.lower()}"
        if news_id in SOURCES and news_id not in DISABLED_SOURCES:
            deck.append(news_id)
    # The trust anchors travel as pairs - a wall card and a video companion
    # from a DIFFERENT brand each, for source variety: BBC with Guardian
    # video, then the NYT with CNN video.
    deck.append("bbc-world")
    deck.append("youtube-guardian")
    deck.append("nytimes")
    deck.append("youtube-cnn")
    # Injection anchors sit at the END of each brand's news+video pair so the
    # pairs never split. Kickstarter's launch feed is English-only, so it
    # seeds only where English is the primary reading language.
    inject_after: dict[str, tuple[str | None, ...]] = {
        # After the politics pair: the science block - one card per distinct
        # bombshell beat (general breakthroughs, space, medicine, fusion, plus
        # a video explainer; no two cards carry the same stories) - then the
        # visitor's IP-based biggest-city card and their property & business
        # cards leading straight into MarketWatch's markets block.
        "propublica": (
            "sci-scientificprogress",
            "youtube-veritasium",
            "sci-spacediscoveries",
            "sci-medicalprogress",
            "sci-fusionprogress",
            "sci-airbornewindenergy",
            COUNTRY_TOP_CITY.get(cc) if cc else None,
            COUNTRY_PROPERTY.get(cc) if cc else None,
            COUNTRY_BUSINESS.get(cc) if cc else None,
        ),
        # The podcast beat - the country's favourite where we carry one, TED
        # Talks Daily everywhere else; English decks get TED alongside their
        # favourite (dedupe collapses the two when TED already was the
        # fallback).
        "heatmap-crypto": (
            COUNTRY_PODCAST.get(cc or "", DEFAULT_PODCAST),
            DEFAULT_PODCAST if cc in _ENGLISH_DECK else None,
        ),
        "nythealth": (COUNTRY_HEALTH.get(cc) if cc else None,),
        "youtube-mrbeast": (COUNTRY_EVENTS.get(cc) if cc else None,),
        "tech-new": (
            COUNTRY_DEALS.get(cc) if cc else None,
            "kickstarter" if cc in _ENGLISH_DECK else None,
        ),
        "youtube-yestheory": (COUNTRY_TRAVEL.get(cc) if cc else None,),
    }
    injected = False
    for sid in DEFAULT_DECK:
        if sid in _GENERIC_SPORTS and country_sports is not None:
            if not injected:
                deck.extend(country_sports)
                injected = True
            continue
        if sid == "heatmap-ucl" and cc and cc in COUNTRY_SPORT_HEATMAPS:
            deck.extend(COUNTRY_SPORT_HEATMAPS[cc])
            continue
        deck.append(sid)
        for extra in inject_after.get(sid, ()):
            if extra:
                deck.append(extra)
    seen: set[str] = set()
    out: list[str] = []
    for sid in deck:
        if sid in seen:
            continue
        seen.add(sid)
        if sid == WEATHER_DECK_ID or (sid in SOURCES and sid not in DISABLED_SOURCES):
            out.append(sid)
    # Playable breaks at the quarter marks of the finished deck; the cube
    # closes it, just ahead of the pinned weather card.
    has_weather = out and out[-1] == WEATHER_DECK_ID
    content = out[:-1] if has_weather else out
    n = len(content)
    for offset, game in enumerate(_GAME_BREAKS):
        if game in SOURCES and game not in DISABLED_SOURCES:
            content.insert(round(n * (offset + 1) / 4) + offset, game)
    if "cube" in SOURCES and "cube" not in DISABLED_SOURCES:
        content.append("cube")
    if has_weather:
        content.append(WEATHER_DECK_ID)
    return content


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
    lang: str = Query("en", min_length=2, max_length=8),
    redis: Redis = Depends(get_redis),
) -> SummaryAvailability:
    """Cheap pre-check for a headline tap: known-unavailable articles (videos,
    paywalls and bot walls seen before, exhausted budget) answer false in a
    few milliseconds so the reader is sent to the article immediately rather
    than after a failed generation."""
    response.headers["Cache-Control"] = "no-store"
    target = translate.canonical_target(lang)
    return SummaryAvailability(
        available=target is not None and await summary.is_available(redis, url, target)
    )


@router.get("/summary/stream", tags=[APITag.public])
async def stream_article_summary(
    url: str = Query(..., min_length=12, max_length=2048),
    lang: str = Query("en", min_length=2, max_length=8),
    redis: Redis = Depends(get_redis),
) -> StreamingResponse:
    """The AI summary as server-sent events, so the panel shows the text as it
    is written: `text` (a whole cached or publisher result), `delta` pieces,
    then `done` - or `error` when the reader should open the article."""

    async def events() -> AsyncIterator[str]:
        # Headers are already on the wire once this runs: a failure here must
        # end the stream with an error event, never a severed connection.
        try:
            target = translate.canonical_target(lang)
            if target is None or not await _summarizable(redis, url):
                yield 'data: {"error": "unavailable"}\n\n'
                return
            async for event in summary.stream_summary(redis, url, target):
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
    lang: str = Query("en", min_length=2, max_length=8),
    redis: Redis = Depends(get_redis),
) -> SummaryResponse:
    """AI summary for a headline tap. One model call per article+language -
    everything else is served from cache (and the edge can cache it too)."""
    target = translate.canonical_target(lang)
    if target is None:
        raise summary.SummaryUnavailable()
    # The allowlist bounds who can aim a fetch and the day's model budget at a
    # URL; a summary already in the cache costs neither. Known-markers expire
    # sooner than the summary cache, so gating on the allowlist alone 502'd
    # readers out of finished summaries.
    if not await _summarizable(redis, url) and not await summary.has_cached(
        redis, url, target
    ):
        raise summary.SummaryUnavailable()
    result = await summary.get_summary_result(redis, url, target)
    response.headers["Cache-Control"] = (
        "public, max-age=3600, s-maxage=86400, stale-while-revalidate=604800"
    )
    response.headers["Vary"] = "Origin"
    return SummaryResponse(summary=result.text, url=url, kind=result.kind)


@router.get("/crossword", response_model=CrosswordResponse, tags=[APITag.public])
async def get_crossword(
    response: Response,
    redis: Redis = Depends(get_redis),
) -> CrosswordResponse:
    """The daily crossword for the wall's puzzle card. One upstream fetch per
    day (Redis-cached); every reader worldwide gets the same puzzle, so the
    payload is fully cacheable at the edge."""
    now = datetime.now(UTC)
    date_str = now.strftime("%y%m%d")
    fallback_date_str = (now - timedelta(days=1)).strftime("%y%m%d")
    puzzle = await games.get_crossword(redis, date_str, fallback_date_str)
    response.headers["Cache-Control"] = (
        "public, max-age=600, s-maxage=3600, stale-while-revalidate=86400"
    )
    response.headers["Vary"] = "Origin"
    return CrosswordResponse.model_validate(puzzle)


@router.get("/templates", response_model=TemplatesResponse, tags=[APITag.public])
async def get_templates(
    response: Response,
    country: str | None = Query(None, min_length=2, max_length=2),
    cf_ipcountry: str | None = Header(None, alias="CF-IPCountry"),
) -> TemplatesResponse:
    """Starter templates: curated source bundles by persona (developer,
    investor, sports fan, …), country-resolved like the default deck. Display
    names live client-side, keyed by template id."""
    # Same anonymous per-country cacheability as /default-deck.
    response.headers["Cache-Control"] = "public, max-age=600, s-maxage=3600"
    response.headers["Vary"] = "Origin, CF-IPCountry"
    # Function-level import: templates.py reads this module's country maps, so
    # a top-level import back at us would be circular.
    from .templates import resolve_templates

    resolved = country or _ip_country(cf_ipcountry)
    cc = resolved.upper() if resolved else None
    return TemplatesResponse.model_validate({"templates": resolve_templates(cc)})


@router.get("/weather", response_model=WeatherResponse, tags=[APITag.public])
async def get_weather(
    latitude: float | None = Query(None, ge=-90, le=90),
    longitude: float | None = Query(None, ge=-180, le=180),
    country: str | None = Query(None, min_length=2, max_length=2),
    cf_ipcountry: str | None = Header(None, alias="CF-IPCountry"),
    redis: Redis = Depends(get_redis),
) -> WeatherResponse:
    """Current conditions and a short forecast for the reader's location. The
    browser sends precise ``latitude``/``longitude`` when geolocation is
    granted; otherwise it sends the IP ``country`` (from Cloudflare) and we
    resolve that country's capital. Proxied from Open-Meteo, cache-first.

    Native clients have no IP-country cookie to read, so when they send neither
    coordinates nor a country we fall back to Cloudflare's header ourselves -
    otherwise a phone whose UI language is US English would be given US weather
    wherever it actually is."""
    result = await weather.get_weather(
        redis, latitude, longitude, country or _ip_country(cf_ipcountry)
    )
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
    # deck-seeded heatmap is an origin hit per reader per poll, which is what
    # amplifies concurrent load into a provider-quota stampede. Vary on Origin
    # for the same CORS reason as /default-deck.
    response.headers["Cache-Control"] = (
        "public, max-age=60, s-maxage=300, stale-while-revalidate=3600"
    )
    response.headers["Vary"] = "Origin"
    return HeatmapResponse.model_validate(result)


@router.post(
    "/translate",
    response_model=TranslateResponse,
    tags=[APITag.public],
)
async def translate_headlines(
    body: TranslateRequest,
    redis: Redis = Depends(get_redis),
) -> TranslateResponse:
    """Translations the wall has already made, for a batch of headlines.
    Cache-only: headlines are translated where they are served (the source
    card endpoints), so a headline the wall has shown in *target* answers
    translated here and anything else is returned unchanged - this route
    never spends model budget on caller-supplied text (see
    translate.cached_translations for why it must not)."""
    target = translate.canonical_target(body.target)
    if target is None or target == "en":
        return TranslateResponse(translations=body.texts)
    translations = await translate.cached_translations(redis, body.texts, target)
    # Demand counts only when the wall really shows this language (>= 1 cache
    # hit): counting every call let an anonymous caller inflate any language's
    # ranking and steer the translation warmer's budget with junk batches.
    # Real readers' demand is counted where cards are served either way.
    if any(
        translated != original for translated, original in zip(translations, body.texts)
    ):
        await translate.note_demand(redis, target)
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
    sources only - search never triggers an outbound fetch). Result headlines
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
    user follows (warm cache only - never triggers a fetch). Headlines are
    translated into ``lang`` when set, like the source cards."""
    source_ids = await follows.list_followed(session, auth_subject.subject.id)
    items = await follows.followed_feed(redis, source_ids)
    return NewsSearchResponse(
        sources=[], items=await _translate_hits(redis, items, lang)
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

# Non-English hero warming is limited to the languages readers are actually
# asking for (the same top-8 ranking the translation warmer invests in):
# without the gate, one caller cycling ?lang= across all 48 canonical codes
# kept the bounded warm queue full of rare-language entries and spent the
# free-tier warm budget on summaries nobody reads. Cached in-process for a
# minute - demanded_targets is a wide MGET, far too heavy per serve.
_WARM_LANG_TOP = 8
_WARM_LANG_CACHE_SECONDS = 60
_warm_langs_cached: tuple[float, frozenset[str]] = (0.0, frozenset())


async def _warmable_lang(redis: Redis, lang: str) -> bool:
    global _warm_langs_cached
    if lang == "en":
        return True
    now = time.monotonic()
    stamp, langs = _warm_langs_cached
    if now - stamp > _WARM_LANG_CACHE_SECONDS:
        # The floor matters as much as the top-8: card serves stamp demand
        # unconditionally (a new language must be able to bootstrap itself),
        # so without it one caller cycling ?lang= could still walk junk
        # languages into the gate. Real audiences clear 200/day without
        # noticing; a spoofer has to sustain real request volume per
        # language, priced by the rate limits, to buy mere warm priority.
        langs = frozenset(
            (await translate.demanded_targets(redis, min_total=200))[:_WARM_LANG_TOP]
        )
        _warm_langs_cached = (now, langs)
    return lang in langs


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
            latest and await _acquire_latest_fetch(redis, resolved)
        ):
            await _keep_known(redis, resolved, entry.items)
            return SourceResponse(
                status="cache",
                id=resolved,
                updated_time=entry.updated,
                items=entry.items,
            )

    if entry is None and not await _acquire_latest_fetch(redis, resolved):
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
        return SourceResponse(
            status="success", id=resolved, updated_time=updated, items=items
        )
    except TimeoutError as exc:
        # Caught before the generic handler for two reasons: `str(TimeoutError())`
        # is empty, so it would log an unreadable failure; and taking the refetch
        # cooldown stops a source that times out every time from spending one of
        # the shared fetch slots on every poll for as long as a tab is open.
        log.info("news.fetch_timeout", source=resolved, seconds=FETCH_TIMEOUT_SECONDS)
        await _acquire_latest_fetch(redis, resolved)
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
        updated = await cache.set(redis, resolved, [])
        return SourceResponse(
            status="success", id=resolved, updated_time=updated, items=[]
        )
    except Exception as exc:  # scrapers parse wild HTML - anything can raise
        log.info("news.fetch_failed", source=resolved, error=str(exc))
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
    """Items for one source - cache-first with the ported TTL semantics. When
    ``lang`` is set the headlines are machine-translated into it before the
    response returns, so the card renders in the reader's language on first
    paint (no English flash, no second round trip). This runs for English
    readers too: the translator auto-detects the source language, so a foreign
    source (e.g. a Croatian or French outlet) is rendered in English for an
    English reader, while an already-English source detects en→en and is
    returned unchanged (and cached), so there's no wasted work after the first
    fetch of each headline."""
    # Case/variant-tolerant ('zh-hans', 'EN'): the raw form silently skipped
    # translation with pending=False, so those readers got frozen English
    # cards that never re-polled.
    lang = translate.canonical_target(lang) if lang else None
    response = await _get_source(redis, source_id, latest=latest)
    if lang and response.items:
        await translate.note_demand(redis, lang)
        titles, pending = await translate.translate_texts_with_status(
            redis, [item.title for item in response.items], lang, block=False
        )
        response.translations_pending = pending
        response.items = [
            item.model_copy(update={"title": title})
            for item, title in zip(response.items, titles)
        ]
    if response.items:
        # Readers tap the top of a card far more than its tail, but "the hero
        # only" left every other tap paying the full cold cost (~9s: article
        # fetch plus a model call). Queue the top few so most taps land on a
        # cache hit; the warmer is free-tier only, daily-capped, and skips
        # anything already cached, so the extra candidates cost nothing once
        # they are warm. Only for languages we actually serve: junk ?lang=
        # values otherwise fill the bounded queue and spend the warmer's
        # budget on summaries nobody can ever read.
        warm_lang = translate.canonical_target(lang) if lang else "en"
        if warm_lang is not None and await _warmable_lang(redis, warm_lang):
            # One batched call, not one per hero: this is the hottest read
            # path, and per-URL queueing cost two Redis round trips EACH
            # (twelve per serve) where the batch costs two total.
            await summary.note_warm_candidates(
                redis,
                [item.url for item in response.items[:_WARM_HERO_COUNT] if item.url],
                warm_lang,
            )
    return response


async def _translate_hits(
    redis: Redis, hits: list[NewsSearchItem], lang: str | None
) -> list[NewsSearchItem]:
    """Machine-translate the headline titles of search/feed hits into *lang*
    (cache-first), returning them unchanged when *lang* is unset. Mirrors the
    per-source card translation so followed-feed and search results also render
    in the reader's language (incl. English readers reading a foreign source)."""
    lang = translate.canonical_target(lang) if lang else None
    if not (lang and hits):
        return hits
    await translate.note_demand(redis, lang)
    titles = await translate.translate_texts(
        redis, [hit.item.title for hit in hits], lang, block=False
    )
    return [
        hit.model_copy(update={"item": hit.item.model_copy(update={"title": title})})
        for hit, title in zip(hits, titles)
    ]


@router.post("/batch", response_model=list[SourceResponse], tags=[APITag.public])
async def batch(
    body: BatchRequest,
    redis: Redis = Depends(get_redis),
) -> Response:
    """Cached items for many sources in one round trip (upstream
    `entire` semantics): NEVER triggers outbound fetches - cold or
    unknown sources are simply absent from the response, and each card
    lazy-fetches its own source as it scrolls into view. This is what
    makes a warm wall render instantly."""

    # Resolve first, then read every payload in ONE MGET. Gathering a GET per
    # source issues up to 256 sequential Redis round trips for a single request
    # - on exactly the path that is supposed to make a warm wall instant.
    resolved_ids: list[str] = []
    seen: set[str] = set()
    for source_id in body.sources:
        resolved = registry.resolve(source_id)
        if resolved is None or resolved in seen:
            continue
        seen.add(resolved)
        resolved_ids.append(resolved)

    # The cached payloads are already the serialized form the response needs
    # (cache.set dumps validated NewsItems by alias), so splice them through
    # as plain JSON. Round-tripping them used to run model_validate on every
    # item AND revalidate + reserialize through response_model - ~7,700
    # models twice for a maxed request, 50-100ms of event-loop CPU an
    # anonymous caller could pin a core with now that ~330 sources are
    # guaranteed warm. Returning a Response keeps the OpenAPI schema from
    # response_model while skipping both pydantic passes.
    results: list[str] = []
    now = cache.now_ms()
    for resolved, raw in await cache.mget_hot_raw(redis, resolved_ids):
        if raw is None:
            continue  # cold or unknown: absent, the card fetches it itself
        try:
            entry = json.loads(raw)
            updated = int(entry["updated"])
            items_json = json.dumps(entry["items"], ensure_ascii=False)
        except (ValueError, KeyError, TypeError):
            continue
        fresh = now - updated < registry.interval_ms(resolved)
        status = "success" if fresh else "cache"
        results.append(
            f'{{"status":"{status}","id":{json.dumps(resolved)},'
            f'"updatedTime":{updated},"items":{items_json},'
            f'"translationsPending":false}}'
        )
    return Response(
        content="[" + ",".join(results) + "]", media_type="application/json"
    )
