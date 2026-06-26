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
from . import cache, follows, registry, search
from .fetch import NewsFetchError, fetch_text, parse_rss
from .metadata import SOURCES
from .schemas import (
    BatchRequest,
    FollowedSources,
    NewsItem,
    NewsSearchResponse,
    SourceMeta,
    SourceResponse,
)
from .sources.reddit import REDDIT_SUBS

log = structlog.get_logger()

router = APIRouter(prefix="/news", tags=["news"])

# Cap concurrent outbound fetches so a cold-cache batch doesn't open a
# connection per source at once.
_fetch_semaphore = asyncio.Semaphore(8)


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
        for source_id, meta in SOURCES.items()
    ]


@router.get("/search", response_model=NewsSearchResponse, tags=[APITag.public])
async def search_news(
    q: str = Query(..., min_length=2, max_length=80, description="Search query."),
    redis: Redis = Depends(get_redis),
) -> NewsSearchResponse:
    """Search the wall: source names (always) and cached headlines (warm
    sources only — search never triggers an outbound fetch)."""
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
    user follows (warm cache only — never triggers a fetch)."""
    source_ids = await follows.list_followed(session, auth_subject.subject.id)
    return NewsSearchResponse(
        sources=[], items=await follows.followed_feed(redis, source_ids)
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


def _reddit_sort_url(sub: str, sort: str) -> str:
    """Build the Reddit RSS URL for *sub* at the given *sort* mode.

    ``top`` appends ``?t=day`` to restrict to the past 24 hours.
    """
    url = f"https://www.reddit.com/r/{sub}/{sort}.rss"
    if sort == "top":
        url += "?t=day"
    return url


async def _fetch_reddit_sorted(sub: str, sort: str) -> list[NewsItem]:
    """Fetch r/{sub}/{sort}.rss and parse it."""
    url = _reddit_sort_url(sub, sort)
    items = parse_rss(await fetch_text(url))
    if not items:
        raise NewsFetchError(f"Cannot fetch rss data for r/{sub}/{sort}")
    return items


async def _get_source(
    redis: Redis, source_id: str, *, latest: bool, sort: str = "hot"
) -> SourceResponse:
    resolved = registry.resolve(source_id)
    if resolved is None:
        raise ResourceNotFound(f"Unknown news source: {source_id}")

    # Non-hot sort is only meaningful for Reddit sources.  For everything else
    # (or when sort=="hot") fall through to the standard getter path.
    use_reddit_sort = sort != "hot" and resolved in REDDIT_SUBS

    now = cache.now_ms()
    entry = await cache.get(redis, resolved, sort)
    if entry is not None:
        # Fresher than the source's own update cadence: serve as-is.
        if now - entry.updated < registry.interval_ms(resolved):
            return SourceResponse(
                status="success", id=resolved, updated_time=now, items=entry.items
            )
        # Stale but within the hard TTL: serve marked as cache, unless the
        # client explicitly asked for the latest.
        if now - entry.updated < cache.TTL_MS and not latest:
            return SourceResponse(
                status="cache",
                id=resolved,
                updated_time=entry.updated,
                items=entry.items,
            )

    try:
        async with _fetch_semaphore:
            if use_reddit_sort:
                items = (await _fetch_reddit_sorted(REDDIT_SUBS[resolved], sort))[:30]
            else:
                getter = registry.GETTERS[resolved]
                items = (await getter())[:30]
        if items:
            await cache.set(redis, resolved, items, sort)
        return SourceResponse(
            status="success", id=resolved, updated_time=now, items=items
        )
    except Exception as exc:  # scrapers parse wild HTML — anything can raise
        log.info("news.fetch_failed", source=resolved, sort=sort, error=str(exc))
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
    sort: str = Query("hot", pattern="^(hot|new|top|rising)$"),
    redis: Redis = Depends(get_redis),
) -> SourceResponse:
    """Items for one source — cache-first with the ported TTL semantics.

    For ``reddit-*`` sources the optional ``sort`` parameter selects
    an alternative feed (``new``, ``top``, ``rising``).  ``top`` is
    scoped to the past day (``?t=day``).  Any other source silently
    ignores the parameter and returns the standard feed.
    """
    return await _get_source(redis, source_id, latest=latest, sort=sort)


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
