"""The tile builders, one module per upstream, each exposing
`fetch_tiles(redis, spec)`. `TILE_BUILDERS` maps a spec's provider id to
its builder; the live signals register theirs in `live/`."""

from collections.abc import Awaitable, Callable
from typing import Any

from outception.redis import Redis

from ..specs import HeatmapSpec
from . import buzz, coingecko, cricket, espn, f1, finnhub, frankfurter, steam
from .live import LIVE_BUILDERS

TileBuilder = Callable[[Redis, HeatmapSpec], Awaitable[list[dict[str, Any]]]]

TILE_BUILDERS: dict[str, TileBuilder] = {
    "finnhub": finnhub.fetch_tiles,
    "coingecko": coingecko.fetch_tiles,
    "frankfurter": frankfurter.fetch_tiles,
    "steam": steam.fetch_tiles,
    "espn": espn.fetch_standings,
    "espn-rankings": espn.fetch_rankings,
    "espn-mma": espn.fetch_fight_card,
    "buzz": buzz.fetch_tiles,
    "cricket": cricket.fetch_tiles,
    "f1": f1.fetch_tiles,
    **LIVE_BUILDERS,
}
