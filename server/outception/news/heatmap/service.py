"""Tables for the wall's table cards, cache-first with serve-stale on
error, on the provider toolkit: a fresh map serves as is; a stale one
serves at once while the single-flight winner refreshes it in the
background; only a cold cache makes the reader wait on the upstream, and
a recent cold failure, a cooling provider or a spent daily budget never
hammer it. Every key keeps its live name."""

import asyncio
import json
import re
from typing import Any

import structlog

from outception.exceptions import OutceptionBackpressureError, OutceptionError
from outception.net import state as signal_state
from outception.net.provider import Toolkit
from outception.redis import Redis

from ..cache import now_ms
from ..fetch import NewsFetchError
from . import specs
from .providers import TILE_BUILDERS
from .providers.buzz import DEMAND_KEY, DEMAND_TTL_SECONDS
from .specs import HARD_TTL_SECONDS, HeatmapSpec, net_spec

log = structlog.get_logger()

CACHE_KEY = "news:heatmap:{id}"
# Single-flight: one refetch of a given map per this window across all
# workers. Losers serve the stale entry, so a crowd hitting a stale map
# cannot fan a burst of duplicate upstream calls out past the providers'
# rate budgets.
REFETCH_KEY = "news:heatmap:refetch:{id}"
REFETCH_COOLDOWN_SECONDS = 30
# Negative cache after a cold failure: without it, every request to a map
# with no cached entry re-fires the full upstream fan-out. Short so
# recovery is quick.
FAIL_KEY = "news:heatmap:fail:{id}"
FAIL_COOLDOWN_SECONDS = 60

_STATUS_RE = re.compile(r"HTTP (\d{3})")

# Strong references to in-flight background refreshes: a bare create_task
# is garbage-collectable mid-flight, which would silently kill the refresh.
_refresh_tasks: set[asyncio.Task[None]] = set()


def _status_of(exc: BaseException) -> int | None:
    match = _STATUS_RE.search(str(exc))
    return int(match.group(1)) if match else None


async def read_cached(redis: Redis, heatmap_id: str) -> dict[str, Any] | None:
    """The cached map, or None when there is none or the entry is not one
    (a malformed or legacy payload must be a miss, not a crash)."""
    raw = await redis.get(CACHE_KEY.format(id=heatmap_id))
    if raw is None:
        return None
    try:
        parsed = json.loads(raw)
    except ValueError:
        return None
    if isinstance(parsed, dict) and "updatedTime" in parsed:
        return parsed
    return None


def _is_fresh(cached: dict[str, Any], interval_ms: int) -> bool:
    try:
        return now_ms() - int(cached["updatedTime"]) < interval_ms
    except TypeError, ValueError:
        return False


async def _refresh_in_background(
    redis: Redis, heatmap_id: str, cached: dict[str, Any] | None
) -> None:
    """Run the refetch detached from the request that armed it, so a stale
    map serves instantly while the new tiles land in cache for the next
    reader. The stale copy is threaded through so a failed refresh serves
    stale instead of arming the cold-failure marker."""
    try:
        await fetch_and_store(redis, heatmap_id, cached=cached)
    except OutceptionError:
        pass  # cold-failure bookkeeping already happened inside
    except Exception as exc:
        log.info("news.heatmap_refresh_failed", heatmap_id=heatmap_id, error=str(exc))


async def get_heatmap(redis: Redis, heatmap_id: str) -> dict[str, Any]:
    spec = specs.HEATMAPS.get(heatmap_id)
    if spec is None or not specs.is_configured(spec):
        raise OutceptionError("Unknown heatmap", status_code=404)
    if spec.provider == "buzz":
        await redis.set(DEMAND_KEY.format(id=heatmap_id), "1", ex=DEMAND_TTL_SECONDS)
    cached = await read_cached(redis, heatmap_id)
    if cached is not None:
        interval = await Toolkit(redis).interval(net_spec(spec))
        if _is_fresh(cached, interval):
            return {**cached, "status": "success"}
        # Stale-while-revalidate: the reader gets the stale tiles now and
        # the single-flight winner refreshes detached from this request.
        won = await redis.set(
            REFETCH_KEY.format(id=heatmap_id), "1", ex=REFETCH_COOLDOWN_SECONDS, nx=True
        )
        if won:
            task = asyncio.create_task(
                _refresh_in_background(redis, heatmap_id, cached)
            )
            _refresh_tasks.add(task)
            task.add_done_callback(_refresh_tasks.discard)
        return {**cached, "status": "cache"}
    # Cold cache: the fetch happens inline, single-flight; losers are told
    # to retry shortly, and a recent cold failure short-circuits.
    won = await redis.set(
        REFETCH_KEY.format(id=heatmap_id), "1", ex=REFETCH_COOLDOWN_SECONDS, nx=True
    )
    if not won:
        raise OutceptionBackpressureError("Heatmap is warming up", status_code=503)
    if await redis.get(FAIL_KEY.format(id=heatmap_id)):
        raise OutceptionBackpressureError("Heatmap is unavailable", status_code=502)
    return await fetch_and_store(redis, heatmap_id, cached=None)


def _finish_tiles(
    spec: HeatmapSpec, tiles: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    if not tiles:
        if spec.live:
            # No storms, no alerts: a real answer. The card carries no tiles
            # and hides itself; a table with nothing to show is a failure.
            return []
        raise NewsFetchError("empty heatmap")
    # A partial fetch must not be cached as an authoritative map, replacing
    # a complete stale one. Only symbol universes have a known target size.
    if spec.symbols and len(tiles) < len(spec.symbols) // 2:
        raise NewsFetchError(f"partial heatmap ({len(tiles)}/{len(spec.symbols)})")
    # Drop only true dust (under 0.1% of the map); after the partial guard
    # on purpose, so filtering cannot fake a half-dead signal.
    total_weight = sum(tile["weight"] for tile in tiles)
    if total_weight > 0:
        tiles = [tile for tile in tiles if tile["weight"] >= total_weight * 0.001]
    # Sports grids read as uniform rosters, not market caps: every team the
    # same size, in standings order; colour carries the standings signal.
    if spec.column == "sports":
        for tile in tiles:
            tile["weight"] = 1.0
    return tiles


async def fetch_and_store(
    redis: Redis, heatmap_id: str, cached: dict[str, Any] | None
) -> dict[str, Any]:
    """One refresh through the toolkit's cooldown and budget, stored under
    the map's key. Serves the stale copy when the refresh cannot happen or
    fails; with no copy, marks the cold failure and raises 502."""
    spec = specs.HEATMAPS[heatmap_id]
    net = net_spec(spec)
    toolkit = Toolkit(redis)

    async def serve_stale(reason: str) -> dict[str, Any]:
        if cached is not None:
            return {**cached, "status": "cache"}
        await redis.set(FAIL_KEY.format(id=heatmap_id), "1", ex=FAIL_COOLDOWN_SECONDS)
        log.info("news.heatmap_failed", heatmap_id=heatmap_id, error=reason)
        raise OutceptionBackpressureError("Heatmap is unavailable", status_code=502)

    if await toolkit.cooldown_remaining(net.id):
        return await serve_stale("provider cooling down")
    if not await toolkit.budget_available(net):
        return await serve_stale("daily budget spent")
    await toolkit.charge_budget(net)
    try:
        tiles = _finish_tiles(spec, await TILE_BUILDERS[spec.provider](redis, spec))
    # Broad on purpose: third-party JSON coercion can raise beyond the fetch
    # errors, and every such surprise must serve stale rather than 500.
    except Exception as exc:
        status = _status_of(exc)
        if status is not None and (status == 429 or status >= 500):
            await toolkit.set_cooldown(net, None)
        await signal_state.note_failure(
            redis, heatmap_id, "quota" if status == 429 else "transient"
        )
        return await serve_stale(str(exc))
    payload = {"id": heatmap_id, "updatedTime": now_ms(), "tiles": tiles}
    await redis.set(
        CACHE_KEY.format(id=heatmap_id), json.dumps(payload), ex=HARD_TTL_SECONDS
    )
    await signal_state.clear_failure(redis, heatmap_id)
    return {**payload, "status": "success"}
