"""The crypto universe: one keyless call for the whole market."""

from typing import Any

from outception.redis import Redis

from ..specs import HeatmapSpec
from . import http

_MARKETS_URL = "https://api.coingecko.com/api/v3/coins/markets"


async def fetch_tiles(redis: Redis, spec: HeatmapSpec) -> list[dict[str, Any]]:
    coins = await http.fetch_json(
        _MARKETS_URL,
        params={
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 30,
            "page": 1,
            "price_change_percentage": "24h",
        },
    )
    tiles: list[dict[str, Any]] = []
    for coin in coins if isinstance(coins, list) else []:
        change = coin.get("price_change_percentage_24h")
        cap = coin.get("market_cap")
        if change is None or not cap:
            continue
        symbol = str(coin.get("symbol", "")).upper()
        tiles.append(
            {
                "symbol": symbol,
                "name": str(coin.get("name", "")),
                "logo": str(coin.get("image") or "") or None,
                "changePercent": round(float(change), 2),
                "price": float(coin.get("current_price") or 0.0),
                "weight": float(cap),
                "url": f"https://finance.yahoo.com/quote/{symbol}-USD",
            }
        )
    return tiles
