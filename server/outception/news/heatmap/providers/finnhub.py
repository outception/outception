"""Stock universes: one quote per symbol plus a slow-moving profile (market cap, logo) cached for a day. Needs a key; without one the stock tables leave the roster."""

import asyncio
import json
from typing import Any

from outception.config import settings
from outception.redis import Redis

from ..specs import HeatmapSpec
from . import http
from .usd_rates import usd_rates

_QUOTE_URL = "https://finnhub.io/api/v1/quote"
_PROFILE_URL = "https://finnhub.io/api/v1/stock/profile2"
_PROFILE_KEY = "news:heatmap:prof:{symbol}"
_CAP_TTL_SECONDS = 24 * 60 * 60
# Nothing real is worth more than this (USD millions): an implausible cap
# means the data is untrustworthy, so the tile is dropped rather than
# rendered at a made-up size.
_CAP_SANITY_MILLIONS = 8_000_000
# The free tier allows 60 calls a minute; a cold category fetch is about
# two calls per symbol. Keep bursts polite.
_semaphore = asyncio.Semaphore(8)


async def _fetch_quote(symbol: str) -> dict[str, Any]:
    async with _semaphore:
        return await http.fetch_json(
            _QUOTE_URL,
            params={"symbol": symbol, "token": settings.FINNHUB_API_KEY},
        )


async def _market_profile(redis: Redis, symbol: str) -> tuple[float, str | None]:
    """(cap in USD millions, logo url), cached for a day - both move slowly
    and only drive tile area/decoration. Unknown, unconvertible or implausible
    caps become 0 and the tile is dropped rather than rendered at a made-up
    size."""
    key = _PROFILE_KEY.format(symbol=symbol)
    cached = await redis.get(key)
    if cached is not None:
        try:
            parsed = json.loads(cached)
            if isinstance(parsed, dict):
                logo = parsed.get("logo")
                return float(parsed["cap"]), str(logo) if logo else None
        except ValueError, KeyError, TypeError:
            pass
    try:
        async with _semaphore:
            profile = await http.fetch_json(
                _PROFILE_URL,
                params={"symbol": symbol, "token": settings.FINNHUB_API_KEY},
            )
        cap = float(profile.get("marketCapitalization") or 0.0)
        currency = str(profile.get("currency") or "USD")
        if cap > 0 and currency != "USD":
            rate = (await usd_rates(redis)).get(currency)
            if not rate:
                return 0.0, None
            cap /= rate
    except http.NewsFetchError:
        return 0.0, None
    if cap > _CAP_SANITY_MILLIONS:
        return 0.0, None
    # Finnhub's own logo URLs 302 to an HTML page (hotlink-blocked), so derive
    # the mark from the company's website via the same favicon service the
    # source badges use.
    weburl = str(profile.get("weburl") or "")
    domain = weburl.split("//")[-1].split("/")[0]
    logo = (
        "https://t0.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON"
        f"&fallback_opts=TYPE,SIZE,URL&url=http://{domain}&size=128"
        if domain
        else None
    )
    if cap > 0:
        await redis.set(
            key, json.dumps({"cap": cap, "logo": logo}), ex=_CAP_TTL_SECONDS
        )
    return cap, logo


async def fetch_tiles(redis: Redis, spec: HeatmapSpec) -> list[dict[str, Any]]:
    async def one(symbol: str, name: str) -> dict[str, Any] | None:
        try:
            quote = await _fetch_quote(symbol)
        except http.NewsFetchError:
            return None
        change = quote.get("dp")
        price = quote.get("c")
        # A symbol Finnhub doesn't know returns zeros across the board.
        if change is None or not price:
            return None
        cap, logo = await _market_profile(redis, symbol)
        if cap <= 0:
            return None
        return {
            "symbol": symbol,
            "name": name,
            "logo": logo,
            "changePercent": round(float(change), 2),
            "price": round(float(price), 2),
            "weight": cap,
            "url": f"https://finance.yahoo.com/quote/{symbol}",
        }

    results = await asyncio.gather(
        *(one(symbol, name) for symbol, name in spec.symbols)
    )
    return [tile for tile in results if tile is not None]
