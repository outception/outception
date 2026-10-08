"""Currency moves against the dollar from central-bank reference rates."""

from datetime import date, timedelta
from typing import Any

from outception.redis import Redis

from ..specs import HeatmapSpec
from . import http

_BASE_URL = "https://api.frankfurter.app"


# ECB reference currencies sized by rough BIS turnover share (relative tile
# areas only, so precision doesn't matter). Change is the CURRENCY's move vs
# USD, so a green EUR tile means the euro strengthened.
_FX_UNIVERSE: tuple[tuple[str, str, float], ...] = (
    ("EUR", "Euro", 31.0),
    ("JPY", "Japanese Yen", 17.0),
    ("GBP", "British Pound", 13.0),
    ("CNY", "Chinese Yuan", 7.0),
    ("AUD", "Australian Dollar", 6.4),
    ("CAD", "Canadian Dollar", 6.2),
    ("CHF", "Swiss Franc", 5.2),
    ("HKD", "Hong Kong Dollar", 2.9),
    ("SGD", "Singapore Dollar", 2.4),
    ("SEK", "Swedish Krona", 2.2),
    ("KRW", "South Korean Won", 2.0),
    ("NOK", "Norwegian Krone", 1.7),
    ("NZD", "New Zealand Dollar", 1.7),
    ("INR", "Indian Rupee", 1.6),
    ("MXN", "Mexican Peso", 1.5),
    ("ZAR", "South African Rand", 1.0),
    ("BRL", "Brazilian Real", 1.0),
    ("DKK", "Danish Krone", 0.7),
    ("PLN", "Polish Złoty", 0.7),
    ("THB", "Thai Baht", 0.4),
    ("TRY", "Turkish Lira", 0.4),
)


async def fetch_tiles(redis: Redis, spec: HeatmapSpec) -> list[dict[str, Any]]:
    """Currency moves vs USD from ECB reference rates. Frankfurter serves
    rates as currency-per-USD, so a currency's own move inverts the ratio:
    strengthened ⇢ fewer units per dollar."""
    symbols = ",".join(code for code, _, _ in _FX_UNIVERSE)
    latest_payload = await http.fetch_json(
        f"{_BASE_URL}/latest?base=USD&symbols={symbols}"
    )
    latest = latest_payload.get("rates") or {}
    prev_day = _previous_business_day(str(latest_payload.get("date", "")))
    prev_payload = await http.fetch_json(
        f"{_BASE_URL}/{prev_day}?base=USD&symbols={symbols}"
    )
    prev = prev_payload.get("rates") or {}
    tiles: list[dict[str, Any]] = []
    for code, name, share in _FX_UNIVERSE:
        rate = latest.get(code)
        rate_prev = prev.get(code)
        if not rate or not rate_prev:
            continue
        change = (float(rate_prev) / float(rate) - 1.0) * 100.0
        tiles.append(
            {
                "symbol": code,
                "name": name,
                # ISO 4217's first two letters are the issuing country
                # (EUR → the "eu" flag flagcdn also serves).
                "logo": f"https://flagcdn.com/w160/{code[:2].lower()}.png",
                "changePercent": round(change, 2),
                "price": round(1.0 / float(rate), 4),
                "weight": share,
                "url": f"https://finance.yahoo.com/quote/{code}USD%3DX",
            }
        )
    return tiles


def _previous_business_day(iso_date: str) -> str:
    try:
        day = date.fromisoformat(iso_date)
    except ValueError:
        return "latest"
    step = day - timedelta(days=1)
    while step.weekday() >= 5:  # Sat/Sun - ECB publishes business days only
        step -= timedelta(days=1)
    return step.isoformat()
