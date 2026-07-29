"""Public news endpoints powering the landing page.

Unauthenticated by design — the landing page is the logged-out surface.
Heavy lifting is cache-first (Redis); a request only triggers an
outbound fetch when the cached copy aged past the source's interval,
and one broken source never takes down a batch.
"""

import asyncio
import hashlib
import json
from datetime import UTC, datetime, timedelta

import structlog
from fastapi import Depends, Header, Query, Request, Response

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
from . import cache, follows, games, heatmap, registry, search, translate, weather
from .cities_data import COUNTRY_TOP_CITY
from .metadata import SOURCES, SourceInfo
from .registry import DISABLED_SOURCES
from .schemas import (
    BatchRequest,
    CrosswordResponse,
    FollowedSources,
    HeatmapResponse,
    NewsSearchItem,
    NewsSearchResponse,
    SourceMeta,
    SourceResponse,
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


# The roster is static — built at import time from the source registry — so
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
async def list_sources(request: Request) -> Response:
    """Metadata for every known source (including redirect aliases)."""
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


# The default "Your deck" for every reader, regardless of location or
# language: a curated spread of major categories in reading order, roughly
# three text sources per category plus a matching YouTube channel where a good
# one exists. A fresh visitor opens onto this spread and then follows/unfollows
# to curate. The weather card isn't a scraped source (no getter, no metadata
# row): it's a synthetic deck entry the frontend renders from the /news/weather
# proxy, and the wall pins it to the end regardless of its position here.
WEATHER_DECK_ID = "weather"

# One representative card per category — the wall now spans far more categories
# (lifestyle, food, travel, culture, faith, …), so the seed is a single strong
# source each rather than 3-4, keeping the fresh-visitor deck broad but light.
DEFAULT_DECK: tuple[str, ...] = (
    # Text and video companions come from DIFFERENT brands on purpose — every
    # pair widens the source variety instead of doubling one outlet.
    "bbc-world",  # World news
    "youtube-guardian",  # …and Guardian News on video
    "thehill",  # Politics
    "propublica",  # …and investigative bombshells
    "marketwatch",  # Business & markets
    "heatmap-tech",  # …and the tech-stocks heatmap card
    "coindesk",  # Crypto
    "heatmap-crypto",  # …and the crypto heatmap card
    # The science/bombshell block rides beside the politics pair (see
    # inject_after); every deck card covers a DISTINCT beat — no two cards
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
    WEATHER_DECK_ID,  # Weather (synthetic — frontend pins it last)
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
    (Tor) and the regional ``EU``/``AP`` codes are sentinels, not countries —
    left in they'd miss the capitals table and silently yield London weather.

    A client can send this header directly, so treat it as a hint, never as a
    trust signal. That is safe here only because both readers map it through a
    closed set (``_CAPITALS`` / the source roster) and the deck response is
    edge-cacheable (``public``) and therefore sends ``Vary: CF-IPCountry`` —
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
    # request Origin — cache one under the other and CORS breaks).
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
    # (their country's source, else nothing — never generic), and each
    # heatmap sitting beside its related news card (crypto map after CoinDesk,
    # sport tables after the sports sources).
    if cc:
        news_id = f"gnews-{cc.lower()}"
        if news_id in SOURCES and news_id not in DISABLED_SOURCES:
            deck.append(news_id)
    # The trust anchors travel as pairs — a wall card and a video companion
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
        # After the politics pair: the science block — one card per distinct
        # bombshell beat (general breakthroughs, space, medicine, fusion, plus
        # a video explainer; no two cards carry the same stories) — then the
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
        # The podcast beat — the country's favourite where we carry one, TED
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
    coordinates nor a country we fall back to Cloudflare's header ourselves —
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
    # same for all), so let the edge/browser cache it — without this, every
    # deck-seeded heatmap is an origin hit per reader per poll, which is what
    # amplifies concurrent load into a provider-quota stampede. Vary on Origin
    # for the same CORS reason as /default-deck.
    response.headers["Cache-Control"] = (
        "public, max-age=60, s-maxage=300, stale-while-revalidate=3600"
    )
    response.headers["Vary"] = "Origin"
    return HeatmapResponse.model_validate(result)


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

# Viewing a source stamps this key so the background warmer
# (tasks.warm_demanded_sources) keeps recently-viewed feeds warm — without it,
# a feed nobody opened in 3h expires from the wall cache and the next reader
# pays the full upstream latency (multi-second for the slower scrapers) on
# first paint. 48h covers a daily reader's gap between visits.
SOURCE_DEMAND_KEY = "news:source:demand:{id}"
SOURCE_DEMAND_TTL_SECONDS = 48 * 60 * 60


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
        # dead or blocking us — a free scraping amplifier.
        raise ResourceNotFound(f"Unknown news source: {source_id}")

    await redis.set(
        SOURCE_DEMAND_KEY.format(id=resolved), "1", ex=SOURCE_DEMAND_TTL_SECONDS
    )
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
        # An empty result still has to advance the cache stamp — skipping the
        # write leaves `updated` stale forever, so every poll sees an expired
        # card and refetches the dead upstream for as long as a tab is open.
        # But don't let a momentary empty (upstream mid-deploy, a selector that
        # matched nothing without raising) throw away good headlines: re-stamp
        # the last known good set instead.
        if not items and entry is not None and entry.items:
            items = entry.items
        updated = await cache.set(redis, resolved, items)
        return SourceResponse(
            status="success", id=resolved, updated_time=updated, items=items
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

    # Resolve first, then read every payload in ONE MGET. Gathering a GET per
    # source issues up to 256 sequential Redis round trips for a single request
    # — on exactly the path that is supposed to make a warm wall instant.
    resolved_ids: list[str] = []
    seen: set[str] = set()
    for source_id in body.sources:
        resolved = registry.resolve(source_id)
        if resolved is None or resolved in seen:
            continue
        seen.add(resolved)
        resolved_ids.append(resolved)

    results: list[SourceResponse] = []
    now = cache.now_ms()
    for resolved, raw in await cache.mget_hot_raw(redis, resolved_ids):
        entry = cache.parse_entry(raw)
        if entry is None:
            continue  # cold or unknown: absent, the card fetches it itself
        fresh = now - entry.updated < registry.interval_ms(resolved)
        results.append(
            SourceResponse(
                status="success" if fresh else "cache",
                id=resolved,
                updated_time=entry.updated,
                items=entry.items,
            )
        )
    return results
