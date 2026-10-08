"""Units-per-USD rates for sizing tiles whose market caps come in the listing currency, cached for a day."""

import json

from outception.redis import Redis

from . import http

_USD_RATES_URL = "https://open.er-api.com/v6/latest/USD"
_USD_RATES_KEY = "news:heatmap:usdrates"
_USD_RATES_TTL_SECONDS = 24 * 60 * 60


async def usd_rates(redis: Redis) -> dict[str, float]:
    """Units-per-USD rates, cached for a day (caps only drive relative tile
    areas, so day-old rates are plenty)."""
    cached = await redis.get(_USD_RATES_KEY)
    if cached is not None:
        try:
            parsed = json.loads(cached)
            if isinstance(parsed, dict):
                return {code: float(rate) for code, rate in parsed.items()}
        except ValueError, TypeError:
            pass
    payload = await http.fetch_json(_USD_RATES_URL)
    raw = payload.get("rates") if isinstance(payload, dict) else None
    rates = {
        str(code): float(rate)
        for code, rate in (raw or {}).items()
        if isinstance(rate, int | float) and rate > 0
    }
    if rates:
        await redis.set(_USD_RATES_KEY, json.dumps(rates), ex=_USD_RATES_TTL_SECONDS)
    return rates
