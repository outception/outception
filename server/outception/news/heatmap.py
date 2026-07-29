"""Market heatmaps for the wall's heatmap cards.

Each heatmap is a curated tile universe (a category of stocks, or the top
crypto coins) served as ``{symbol, name, changePercent, weight}`` tiles the
clients lay out as a squarified treemap - tile area from ``weight`` (market
cap), color from ``changePercent``.

Stocks come from Finnhub (``/quote`` per symbol, free tier: 60 calls/min) and
need ``OUTCEPTION_FINNHUB_API_KEY``; without a key the stock heatmaps are
dropped from the roster so no broken cards show. Market caps (tile sizing)
change slowly, so they're cached for a day while quotes follow the normal
freshness window. Crypto comes from CoinGecko's keyless ``/coins/markets``
(one call for the whole universe).

Cache semantics mirror ``cache.py``: fresher than ``HEATMAP_INTERVAL_MS`` is
served as ``status:"success"`` without refetching; staler entries trigger a
refetch but fall back to the cached payload (``status:"cache"``) when the
upstream fails; only a cold cache with a failing upstream is an error.
"""

import asyncio
import json
import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any
from urllib.parse import quote_plus

import structlog

from outception.config import settings
from outception.exceptions import OutceptionError
from outception.redis import Redis

from .cache import mget_hot_raw, now_ms, parse_entry
from .fetch import NewsFetchError, fetch_html, fetch_json

log = structlog.get_logger()

HEATMAP_INTERVAL_MS = 5 * 60 * 1000
_HARD_TTL_SECONDS = 24 * 60 * 60  # serve-stale window; well past a weekend gap
_CAP_TTL_SECONDS = 24 * 60 * 60

_CACHE_KEY = "news:heatmap:{id}"
# Cached slow-moving profile bits: {"cap": USD millions, "logo": url}.
# (Earlier cap-only keys - cap:/cap2: - are orphaned, not migrated: cap2
# briefly held caps without logos, and before that raw listing-currency
# values.)
_PROFILE_KEY = "news:heatmap:prof:{symbol}"
# Single-flight: one refetch of a given map per this window across all workers
# (mirrors endpoints._acquire_latest_fetch). Losers serve the stale entry, so a
# crowd hitting a stale map can't fan a burst of duplicate upstream calls out
# past the providers' rate budgets (finnhub 60/min, cricketdata 100/DAY).
_REFETCH_KEY = "news:heatmap:refetch:{id}"
_REFETCH_COOLDOWN_SECONDS = 30
# Negative cache after a cold failure: without it, every request to a map with
# no cached entry re-fires the full upstream fan-out (a self-inflicted 429
# storm that stops the map ever warming). Short so recovery is quick.
_FAIL_KEY = "news:heatmap:fail:{id}"
_FAIL_COOLDOWN_SECONDS = 60
# Buzz maps read the wall cache, which only fills when readers browse those
# feeds - a family nobody opened in the last 3h renders an empty map. Viewing a
# buzz map stamps this key so the background warmer (tasks.warm_buzz_sources)
# keeps exactly the demanded families warm, instead of hammering all ~5k buzz
# feeds around the clock. 48h covers a daily reader's gap between visits.
_DEMAND_KEY = "news:heatmap:demand:{id}"
_DEMAND_TTL_SECONDS = 48 * 60 * 60

_FINNHUB_QUOTE_URL = "https://finnhub.io/api/v1/quote"
_FINNHUB_PROFILE_URL = "https://finnhub.io/api/v1/stock/profile2"
_COINGECKO_MARKETS_URL = "https://api.coingecko.com/api/v3/coins/markets"
# Finnhub's profile2 reports marketCapitalization in the company's LISTING
# currency (TSM in TWD, Toyota in JPY, Novo in DKK, …) - sizing tiles by the
# raw number makes TSM ~11x NVDA. Convert with daily keyless USD rates
# (open.er-api.com covers TWD etc.; frankfurter/ECB does not).
_USD_RATES_URL = "https://open.er-api.com/v6/latest/USD"
_USD_RATES_KEY = "news:heatmap:usdrates"
_USD_RATES_TTL_SECONDS = 24 * 60 * 60
# Nothing real is worth more than this (USD millions). Finnhub sometimes
# mislabels a foreign-currency cap as USD (SQM reports its CLP cap as "USD" -
# a $17T lithium miner); an implausible cap means the data is untrustworthy,
# so the tile is dropped rather than rendered at a made-up size.
_CAP_SANITY_MILLIONS = 8_000_000

# Free tier allows 60 calls/min; a cold category fetch is ~2 calls per symbol
# (quote + uncached profile). Keep bursts polite so two cold categories in the
# same minute don't trip the limit.
_finnhub_semaphore = asyncio.Semaphore(8)


@dataclass(frozen=True)
class HeatmapSpec:
    name: str
    desc: str
    color: str
    # "finnhub" | "coingecko" | "frankfurter" | "steam" | "espn"
    # | "f1"
    provider: str
    # (symbol, display name); finnhub universes only
    symbols: tuple[tuple[str, str], ...] = ()
    # Roster column ("finance" for markets, "sports" for result grids)
    column: str = "finance"
    # Provider-specific selector: ESPN "{sport}/{league}" path
    # ("football/nfl", "soccer/eng.1").
    code: str = ""
    # Freshness window; rate-capped providers stretch it (cricketdata.org
    # allows 100 req/day, so cricket refreshes at most every 15 minutes).
    interval_ms: int = HEATMAP_INTERVAL_MS
    # ESPN standings only: points-table sports (soccer, rugby) size tiles by
    # table points; win-loss sports (NFL, NBA, …) by wins.
    table: bool = False
    # Standings qualification zones, checked against each competition's actual
    # rules: top `zone_green` qualify outright (Champions League spots,
    # playoff berths) and burn green; the next `zone_soft` are the softer
    # qualification band (Europa/Conference, play-in) in light green; the
    # bottom `zone_red` are the drop zone (relegation, league-phase
    # elimination) in red, preceded by `zone_red_soft` (relegation playoff) in
    # light red. Everyone else reads neutral. For grouped standings (NFL
    # conferences, MLB leagues) zones apply per group. All zero = keep the
    # provider's own heat (form/streak).
    zone_green: int = 0
    zone_soft: int = 0
    zone_red: int = 0
    zone_red_soft: int = 0
    # Buzz maps over per-country families: leading phrase to strip from source
    # names so tiles read "Ireland", not "Property Irela…".
    strip: str = ""


# Curated universes, ~2 dozen liquid names each - enough for a card-sized
# treemap (deeper long-tails render as unreadable slivers on a phone card).
HEATMAPS: dict[str, HeatmapSpec] = {
    "heatmap-tech": HeatmapSpec(
        name="Tech Stocks",
        desc="Big tech at a glance: tiles sized by market cap, colored by today's move",
        color="teal",
        provider="finnhub",
        symbols=(
            ("AAPL", "Apple"),
            ("MSFT", "Microsoft"),
            ("NVDA", "Nvidia"),
            ("GOOGL", "Alphabet"),
            ("AMZN", "Amazon"),
            ("META", "Meta"),
            ("AVGO", "Broadcom"),
            ("TSM", "TSMC"),
            ("ORCL", "Oracle"),
            ("CRM", "Salesforce"),
            ("AMD", "AMD"),
            ("ADBE", "Adobe"),
            ("NFLX", "Netflix"),
            ("INTC", "Intel"),
            ("QCOM", "Qualcomm"),
            ("TXN", "Texas Instruments"),
            ("IBM", "IBM"),
            ("NOW", "ServiceNow"),
            ("UBER", "Uber"),
            ("SHOP", "Shopify"),
            ("PLTR", "Palantir"),
            ("SNOW", "Snowflake"),
            ("SPOT", "Spotify"),
            ("ARM", "Arm"),
        ),
    ),
    "heatmap-finance": HeatmapSpec(
        name="Finance Stocks",
        desc="Banks, payments and asset managers: sized by market cap, colored by today's move",
        color="green",
        provider="finnhub",
        symbols=(
            ("BRK.B", "Berkshire"),
            ("JPM", "JPMorgan"),
            ("V", "Visa"),
            ("MA", "Mastercard"),
            ("BAC", "Bank of America"),
            ("WFC", "Wells Fargo"),
            ("GS", "Goldman Sachs"),
            ("MS", "Morgan Stanley"),
            ("AXP", "American Express"),
            ("C", "Citigroup"),
            ("BLK", "BlackRock"),
            ("SCHW", "Charles Schwab"),
            ("PYPL", "PayPal"),
            ("COIN", "Coinbase"),
            ("HOOD", "Robinhood"),
            ("SPGI", "S&P Global"),
            ("CB", "Chubb"),
            ("PGR", "Progressive"),
        ),
    ),
    "heatmap-health": HeatmapSpec(
        name="Health Stocks",
        desc="Pharma, biotech and insurers: sized by market cap, colored by today's move",
        color="red",
        provider="finnhub",
        symbols=(
            ("LLY", "Eli Lilly"),
            ("UNH", "UnitedHealth"),
            ("JNJ", "Johnson & Johnson"),
            ("NVO", "Novo Nordisk"),
            ("ABBV", "AbbVie"),
            ("MRK", "Merck"),
            ("TMO", "Thermo Fisher"),
            ("ABT", "Abbott"),
            ("AZN", "AstraZeneca"),
            ("PFE", "Pfizer"),
            ("DHR", "Danaher"),
            ("AMGN", "Amgen"),
            ("ISRG", "Intuitive Surgical"),
            ("BMY", "Bristol Myers"),
            ("GILD", "Gilead"),
            ("CVS", "CVS Health"),
            ("MRNA", "Moderna"),
        ),
    ),
    "heatmap-energy": HeatmapSpec(
        name="Energy Stocks",
        desc="Oil, gas and power: sized by market cap, colored by today's move",
        color="orange",
        provider="finnhub",
        symbols=(
            ("XOM", "ExxonMobil"),
            ("CVX", "Chevron"),
            ("SHEL", "Shell"),
            ("TTE", "TotalEnergies"),
            ("BP", "BP"),
            ("COP", "ConocoPhillips"),
            ("SLB", "SLB"),
            ("EOG", "EOG Resources"),
            ("OXY", "Occidental"),
            ("NEE", "NextEra"),
            ("DUK", "Duke Energy"),
            ("SO", "Southern Company"),
            ("GEV", "GE Vernova"),
            ("FSLR", "First Solar"),
            ("VST", "Vistra"),
            ("CEG", "Constellation"),
        ),
    ),
    "heatmap-ev-battery": HeatmapSpec(
        name="EV & Battery Stocks",
        desc="Electric vehicles and battery makers: sized by market cap, colored by today's move",
        color="cyan",
        provider="finnhub",
        symbols=(
            ("TSLA", "Tesla"),
            ("BYDDY", "BYD"),
            ("RIVN", "Rivian"),
            ("LCID", "Lucid"),
            ("NIO", "NIO"),
            ("XPEV", "XPeng"),
            ("LI", "Li Auto"),
            ("GM", "General Motors"),
            ("F", "Ford"),
            ("TM", "Toyota"),
            ("HMC", "Honda"),
            ("ALB", "Albemarle"),
            ("SQM", "SQM"),
            ("PCRFY", "Panasonic"),
            ("ENPH", "Enphase"),
            ("QS", "QuantumScape"),
            ("CHPT", "ChargePoint"),
        ),
    ),
    "heatmap-consumer": HeatmapSpec(
        name="Consumer Stocks",
        desc="Retail, food and household names: sized by market cap, colored by today's move",
        color="purple",
        provider="finnhub",
        symbols=(
            ("WMT", "Walmart"),
            ("COST", "Costco"),
            ("PG", "Procter & Gamble"),
            ("KO", "Coca-Cola"),
            ("PEP", "PepsiCo"),
            ("MCD", "McDonald's"),
            ("NKE", "Nike"),
            ("SBUX", "Starbucks"),
            ("HD", "Home Depot"),
            ("LOW", "Lowe's"),
            ("TGT", "Target"),
            ("DIS", "Disney"),
            ("ABNB", "Airbnb"),
            ("BKNG", "Booking"),
            ("CMG", "Chipotle"),
            ("LULU", "Lululemon"),
        ),
    ),
    "heatmap-crypto": HeatmapSpec(
        name="Crypto Market",
        desc="Top coins by market cap, colored by 24h move",
        color="yellow",
        provider="coingecko",
    ),
    "heatmap-fx": HeatmapSpec(
        name="FX",
        desc="Major currencies vs the US dollar: sized by trading volume, colored by the latest move",
        color="blue",
        provider="frankfurter",
    ),
    "heatmap-steam": HeatmapSpec(
        name="Steam",
        desc="Most-played games right now: sized by players in game, colored by change since yesterday",
        color="indigo",
        provider="steam",
    ),
    # Soccer table grids (ESPN standings, keyless): tiles are teams sized by
    # points, colored by qualification zones once games have been played.
    "heatmap-ucl": HeatmapSpec(
        name="Champions League Table",
        desc="Every club sized by points, colored by recent form",
        color="mediumslateblue",
        provider="espn",
        column="sports",
        code="soccer/uefa.champions",
        table=True,
        # League phase: 1-8 straight to the R16, 9-24 play the knockout
        # playoff, 25-36 are out.
        zone_green=8,
        zone_soft=16,
        zone_red=12,
    ),
    "heatmap-premier-league": HeatmapSpec(
        name="Premier League Table",
        desc="The table as a heat grid: size by points, color by form",
        color="mediumpurple",
        provider="espn",
        column="sports",
        code="soccer/eng.1",
        table=True,
        zone_green=4,
        zone_soft=2,
        zone_red=3,
    ),
    "heatmap-la-liga": HeatmapSpec(
        name="La Liga Table",
        desc="The table as a heat grid: size by points, color by form",
        color="crimson",
        provider="espn",
        column="sports",
        code="soccer/esp.1",
        table=True,
        zone_green=4,
        zone_soft=2,
        zone_red=3,
    ),
    "heatmap-bundesliga": HeatmapSpec(
        name="Bundesliga Table",
        desc="The table as a heat grid: size by points, color by form",
        color="firebrick",
        provider="espn",
        column="sports",
        code="soccer/ger.1",
        table=True,
        zone_green=4,
        zone_soft=2,
        zone_red_soft=1,
        zone_red=2,
    ),
    "heatmap-serie-a": HeatmapSpec(
        name="Serie A Table",
        desc="The table as a heat grid: size by points, color by form",
        color="seagreen",
        provider="espn",
        column="sports",
        code="soccer/ita.1",
        table=True,
        zone_green=4,
        zone_soft=2,
        zone_red=3,
    ),
    "heatmap-ligue-1": HeatmapSpec(
        name="Ligue 1 Table",
        desc="The table as a heat grid: size by points, color by form",
        color="goldenrod",
        provider="espn",
        column="sports",
        code="soccer/fra.1",
        table=True,
        zone_green=3,
        zone_soft=1,
        zone_red_soft=1,
        zone_red=2,
    ),
    "heatmap-championship": HeatmapSpec(
        name="Championship Table",
        desc="The table as a heat grid: size by points, color by form",
        color="steelblue",
        provider="espn",
        column="sports",
        code="soccer/eng.2",
        table=True,
        # 24 teams: top 2 promoted, 3-6 playoff, bottom 3 relegated.
        zone_green=2,
        zone_soft=4,
        zone_red=3,
    ),
    "heatmap-eredivisie": HeatmapSpec(
        name="Eredivisie Table",
        desc="The table as a heat grid: size by points, color by form",
        color="darkorange",
        provider="espn",
        column="sports",
        code="soccer/ned.1",
        table=True,
        # 18 teams: top 2 Champions League, 3-4 Europa/Conference route,
        # 16th relegation playoff, bottom 2 relegated.
        zone_green=2,
        zone_soft=2,
        zone_red_soft=1,
        zone_red=2,
    ),
    "heatmap-primeira-liga": HeatmapSpec(
        name="Primeira Liga Table",
        desc="The table as a heat grid: size by points, color by form",
        color="seagreen",
        provider="espn",
        column="sports",
        code="soccer/por.1",
        table=True,
        # 18 teams: top 2 Champions League, 3-4 Europa/Conference route,
        # 16th relegation playoff, bottom 2 relegated.
        zone_green=2,
        zone_soft=2,
        zone_red_soft=1,
        zone_red=2,
    ),
    "heatmap-brasileirao": HeatmapSpec(
        name="Brasileirão Table",
        desc="The table as a heat grid: size by points, color by form",
        color="forestgreen",
        provider="espn",
        column="sports",
        code="soccer/bra.1",
        table=True,
        # 20 teams: top 4 Libertadores, 5-6 qualifiers/Sudamericana, bottom 4
        # relegated.
        zone_green=4,
        zone_soft=2,
        zone_red=4,
    ),
    # US big-4 standings grids (ESPN's public standings JSON, keyless): tiles
    # sized by wins, colored by the current streak, labelled with the record.
    "heatmap-nfl": HeatmapSpec(
        name="NFL Table",
        desc="Every team sized by wins, colored by streak",
        color="darkolivegreen",
        provider="espn",
        column="sports",
        code="football/nfl",
        zone_green=7,
    ),
    "heatmap-nba": HeatmapSpec(
        name="NBA Table",
        desc="Every team sized by wins, colored by streak",
        color="darkorange",
        provider="espn",
        column="sports",
        code="basketball/nba",
        zone_green=6,
        zone_soft=4,
    ),
    "heatmap-mlb": HeatmapSpec(
        name="MLB Table",
        desc="Every team sized by wins, colored by streak",
        color="steelblue",
        provider="espn",
        column="sports",
        code="baseball/mlb",
        zone_green=6,
    ),
    "heatmap-nhl": HeatmapSpec(
        name="NHL Table",
        desc="Every team sized by wins, colored by streak",
        color="slategray",
        provider="espn",
        column="sports",
        code="hockey/nhl",
        zone_green=8,
    ),
    "heatmap-wnba": HeatmapSpec(
        name="WNBA Table",
        desc="Every team sized by wins, colored by streak",
        color="darkmagenta",
        provider="espn",
        column="sports",
        code="basketball/wnba",
        zone_green=4,
    ),
    "heatmap-mls": HeatmapSpec(
        name="MLS Table",
        desc="The table as a heat grid: size by points, color by places moved",
        color="dodgerblue",
        provider="espn",
        column="sports",
        code="soccer/usa.1",
        table=True,
        zone_green=7,
        zone_soft=2,
    ),
    "heatmap-liga-mx": HeatmapSpec(
        name="Liga MX Table",
        desc="The table as a heat grid: size by points, color by places moved",
        color="forestgreen",
        provider="espn",
        column="sports",
        code="soccer/mex.1",
        table=True,
        zone_green=6,
        zone_soft=4,
    ),
    # Rugby tables (ESPN, keyless - same standings shape as soccer).
    "heatmap-premiership-rugby": HeatmapSpec(
        name="Premiership Rugby Table",
        desc="The table as a heat grid: size by points, color by places moved",
        color="rebeccapurple",
        provider="espn",
        column="sports",
        code="rugby/267979",
        table=True,
        zone_green=4,
    ),
    "heatmap-urc": HeatmapSpec(
        name="URC Table",
        desc="The table as a heat grid: size by points, color by places moved",
        color="darkgreen",
        provider="espn",
        column="sports",
        code="rugby/270557",
        table=True,
        zone_green=8,
    ),
    "heatmap-top14": HeatmapSpec(
        name="Top 14 Table",
        desc="The table as a heat grid: size by points, color by places moved",
        color="navy",
        provider="espn",
        column="sports",
        code="rugby/270559",
        table=True,
        zone_green=2,
        zone_soft=4,
        zone_red_soft=1,
        zone_red=1,
    ),
    # Poll/ranking grids (ESPN rankings, keyless): tiles sized by poll points
    # or ranking points, colored by places moved, labelled with the rank.
    "heatmap-college-football": HeatmapSpec(
        name="College Football Top 25 Table",
        desc="The Top 25 as a heat grid: size by poll points, color by places moved",
        color="saddlebrown",
        provider="espn-rankings",
        column="sports",
        code="football/college-football",
    ),
    "heatmap-atp": HeatmapSpec(
        name="ATP Tennis Table",
        desc="The top 25 as a heat grid: size by ranking points, color by places moved",
        color="olivedrab",
        provider="espn-rankings",
        column="sports",
        code="tennis/atp",
    ),
    "heatmap-wta": HeatmapSpec(
        name="WTA Tennis Table",
        desc="The top 25 as a heat grid: size by ranking points, color by places moved",
        color="palevioletred",
        provider="espn-rankings",
        column="sports",
        code="tennis/wta",
    ),
    # Live golf leaderboard (ESPN, keyless): the current tournament's top of
    # the board - under par burns green, over par red.
    # UFC fight card grid (ESPN scoreboard, keyless): the nearest event's
    # bouts - finished fights show their result, upcoming ones the date.
    "heatmap-ufc": HeatmapSpec(
        name="UFC",
        desc="The next fight card at a glance: results as they land",
        color="maroon",
        provider="espn-mma",
        column="sports",
        code="mma/ufc",
    ),
    # Buzz maps for the wall's entity families: tiles sized by story count,
    # glowing by freshness, all read from our own cache with zero external
    # calls.
    "heatmap-youtube-buzz": HeatmapSpec(
        name="YouTube Buzz",
        desc="Which channels are posting right now: fresher videos glow",
        color="indianred",
        provider="buzz",
        column="entertainment",
        code="youtube-",
    ),
    "heatmap-cities-buzz": HeatmapSpec(
        name="Cities Buzz",
        desc="Which cities are making news right now: fresher stories glow",
        color="lightseagreen",
        provider="buzz",
        column="cities",
        code="city-",
    ),
    "heatmap-world-buzz": HeatmapSpec(
        name="World Buzz",
        desc="Which countries are making news right now: fresher stories glow",
        color="royalblue",
        provider="buzz",
        column="world",
        code="gnews-",
    ),
    # Per-country vertical buzz maps ("which countries is this vertical hot
    # in"): tiles are countries, sized/colored by that country's story volume
    # and freshness for the vertical.
    "heatmap-property-buzz": HeatmapSpec(
        name="Property Buzz",
        desc="Where property is making news right now: fresher stories glow",
        color="burlywood",
        provider="buzz",
        column="property",
        code="property-",
        strip="Property ",
    ),
    "heatmap-business-buzz": HeatmapSpec(
        name="Business Buzz",
        desc="Where business is making news right now: fresher stories glow",
        color="darkseagreen",
        provider="buzz",
        column="finance",
        code="business-",
        strip="Business ",
    ),
    "heatmap-events-buzz": HeatmapSpec(
        name="Events Buzz",
        desc="Where events are making news: fresher stories glow",
        color="plum",
        provider="buzz",
        column="entertainment",
        code="events-",
        strip="Events ",
    ),
    "heatmap-weather-buzz": HeatmapSpec(
        name="Weather Alerts Buzz",
        desc="Where severe weather is making news: fresher stories glow",
        color="skyblue",
        provider="buzz",
        column="news",
        code="wxwarn-",
        strip="Weather ",
    ),
    "heatmap-health-buzz": HeatmapSpec(
        name="Health Buzz",
        desc="Where health is making news: fresher stories glow",
        color="palegreen",
        provider="buzz",
        column="science",
        code="health-",
        strip="Health ",
    ),
    "heatmap-deals-buzz": HeatmapSpec(
        name="Deals Buzz",
        desc="Where the best deals are surfacing: fresher finds glow",
        color="orange",
        provider="buzz",
        column="deals",
        code="deals-",
        strip="Deals ",
    ),
    "heatmap-lifestyle-buzz": HeatmapSpec(
        name="Lifestyle Buzz",
        desc="Which lifestyle topics are making news: fresher stories glow",
        color="thistle",
        provider="buzz",
        column="lifestyle",
        code="life-",
    ),
    # Cricket now-playing grid (cricketdata.org): live and recent matches as
    # equal tiles - live games burn green, finished ones sit faint.
    "heatmap-cricket": HeatmapSpec(
        name="Cricket",
        desc="Live and recent matches at a glance: live games glow",
        color="mediumseagreen",
        provider="cricket",
        column="sports",
        interval_ms=15 * 60 * 1000,
    ),
    # F1 championship grid (Jolpica/Ergast, keyless): drivers sized by points,
    # colored by how they scored in the last race.
    "heatmap-f1": HeatmapSpec(
        name="F1 Table",
        desc="The championship as a heat grid: size by points, color by the last race",
        color="orangered",
        provider="f1",
        column="sports",
    ),
}

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

_FRANKFURTER_URL = "https://api.frankfurter.app"
_CRICKETDATA_URL = "https://api.cricapi.com/v1/currentMatches"
_ESPN_STANDINGS_URL = "https://site.api.espn.com/apis/v2/sports"
# ESPN's edge 403s browser User-Agents that lack a real browser TLS
# fingerprint (bot heuristic) but accepts an honest client UA - so these
# fetches identify as what they are instead of the shared browser UA.
_ESPN_HEADERS = {"User-Agent": "python-httpx"}
_ESPN_SITE_URL = "https://site.api.espn.com/apis/site/v2/sports"
_F1_URL = "https://api.jolpi.ca/ergast/f1"
_STEAM_STATS_URL = "https://store.steampowered.com/stats/stats/"
# Yesterday's Steam player counts, rotated once per UTC day so "change since
# yesterday" survives restarts. Value: JSON {url: players}.
_STEAM_PREV_KEY = "news:heatmap:steam:prev"
_STEAM_PREV_DATE_KEY = "news:heatmap:steam:prev-date"


def available_heatmap_ids() -> list[str]:
    """Heatmaps that can actually be served with the current configuration -
    stock maps need a Finnhub key, cricket a cricketdata key; the rest
    (crypto, fx, steam, ESPN incl. all soccer tables, F1) are keyless."""

    def configured(spec: HeatmapSpec) -> bool:
        if spec.provider == "finnhub":
            return bool(settings.FINNHUB_API_KEY)
        if spec.provider == "cricket":
            return bool(settings.CRICKETDATA_API_KEY)
        return True

    return [heatmap_id for heatmap_id, spec in HEATMAPS.items() if configured(spec)]


async def _fetch_quote(symbol: str) -> dict[str, Any]:
    async with _finnhub_semaphore:
        return await fetch_json(
            _FINNHUB_QUOTE_URL,
            params={"symbol": symbol, "token": settings.FINNHUB_API_KEY},
        )


async def _usd_rates(redis: Redis) -> dict[str, float]:
    """Units-per-USD rates, cached for a day (caps only drive relative tile
    areas, so day-old rates are plenty)."""
    cached = await redis.get(_USD_RATES_KEY)
    if cached is not None:
        try:
            parsed = json.loads(cached)
            if isinstance(parsed, dict):
                return {code: float(rate) for code, rate in parsed.items()}
        except (ValueError, TypeError):
            pass
    payload = await fetch_json(_USD_RATES_URL)
    raw = payload.get("rates") if isinstance(payload, dict) else None
    rates = {
        str(code): float(rate)
        for code, rate in (raw or {}).items()
        if isinstance(rate, int | float) and rate > 0
    }
    if rates:
        await redis.set(_USD_RATES_KEY, json.dumps(rates), ex=_USD_RATES_TTL_SECONDS)
    return rates


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
        except (ValueError, KeyError, TypeError):
            pass
    try:
        async with _finnhub_semaphore:
            profile = await fetch_json(
                _FINNHUB_PROFILE_URL,
                params={"symbol": symbol, "token": settings.FINNHUB_API_KEY},
            )
        cap = float(profile.get("marketCapitalization") or 0.0)
        currency = str(profile.get("currency") or "USD")
        if cap > 0 and currency != "USD":
            rate = (await _usd_rates(redis)).get(currency)
            if not rate:
                return 0.0, None
            cap /= rate
    except NewsFetchError:
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


async def _fetch_finnhub_tiles(redis: Redis, spec: HeatmapSpec) -> list[dict[str, Any]]:
    async def one(symbol: str, name: str) -> dict[str, Any] | None:
        try:
            quote = await _fetch_quote(symbol)
        except NewsFetchError:
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


async def _fetch_coingecko_tiles() -> list[dict[str, Any]]:
    coins = await fetch_json(
        _COINGECKO_MARKETS_URL,
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


async def _fetch_frankfurter_tiles() -> list[dict[str, Any]]:
    """Currency moves vs USD from ECB reference rates. Frankfurter serves
    rates as currency-per-USD, so a currency's own move inverts the ratio:
    strengthened ⇢ fewer units per dollar."""
    symbols = ",".join(code for code, _, _ in _FX_UNIVERSE)
    latest_payload = await fetch_json(
        f"{_FRANKFURTER_URL}/latest?base=USD&symbols={symbols}"
    )
    latest = latest_payload.get("rates") or {}
    prev_day = _previous_business_day(str(latest_payload.get("date", "")))
    prev_payload = await fetch_json(
        f"{_FRANKFURTER_URL}/{prev_day}?base=USD&symbols={symbols}"
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


async def _fetch_steam_tiles(redis: Redis) -> list[dict[str, Any]]:
    """Most-played Steam games by live player count. Duplicates the small
    stats-page parse from sources/steam.py deliberately: importing that module
    here would cycle metadata → heatmap → sources → registry → metadata.
    Yesterday's counts rotate through Redis so color = change since yesterday
    (0 on the first ever fetch)."""
    soup = await fetch_html(_STEAM_STATS_URL)
    current: dict[str, tuple[str, int]] = {}
    for el in soup.select("#detailStats tr.player_count_row"):
        link = el.select_one("a.gameLink")
        players_el = el.select_one("td:first-child .currentServers")
        if link is None or players_el is None:
            continue
        url = str(link.get("href") or "")
        name = link.get_text(strip=True)
        try:
            players = int(players_el.get_text(strip=True).replace(",", ""))
        except ValueError:
            continue
        if url and name and players > 0:
            current[url] = (name, players)
    if not current:
        return []

    today = str(now_ms() // 86_400_000)  # UTC day ordinal
    prev_date = await redis.get(_STEAM_PREV_DATE_KEY)
    prev_raw = await redis.get(_STEAM_PREV_KEY)
    prev: dict[str, int] = {}
    if prev_raw is not None:
        try:
            prev = {k: int(v) for k, v in json.loads(prev_raw).items()}
        except (ValueError, TypeError, AttributeError):
            prev = {}
    prev_str = prev_date.decode() if isinstance(prev_date, bytes) else prev_date
    if prev_str != today:
        # New UTC day: today's counts become tomorrow's baseline.
        await redis.set(
            _STEAM_PREV_KEY,
            json.dumps({url: players for url, (_, players) in current.items()}),
            ex=3 * 86_400,
        )
        await redis.set(_STEAM_PREV_DATE_KEY, today, ex=3 * 86_400)

    tiles: list[dict[str, Any]] = []
    for url, (name, players) in list(current.items())[:24]:
        baseline = prev.get(url)
        change = (players / baseline - 1.0) * 100.0 if baseline and prev_str else 0.0
        # Store links carry the appid, and Steam's CDN serves capsule art by
        # appid - no extra request needed.
        app_match = re.search(r"/app/(\d+)", url)
        logo = (
            f"https://cdn.cloudflare.steamstatic.com/steam/apps/{app_match.group(1)}/capsule_184x69.jpg"
            if app_match
            else None
        )
        tiles.append(
            {
                "symbol": name if len(name) <= 14 else f"{name[:13]}…",
                "name": name,
                "logo": logo,
                "changePercent": round(change, 2),
                "price": float(players),
                "weight": float(players),
                "url": url,
            }
        )
    return tiles


def _zone_heat(spec: HeatmapSpec, position: int, total: int) -> float:
    """Standings color from the competition's qualification zones (see the
    zone_* spec fields): qualification burns green, the drop zone red, the
    soft bands lighter, mid-table neutral."""
    if position <= spec.zone_green:
        return 3.0
    if position <= spec.zone_green + spec.zone_soft:
        return 1.2
    if position > total - spec.zone_red:
        return -3.0
    if position > total - spec.zone_red - spec.zone_red_soft:
        return -1.2
    return 0.0


def _has_zones(spec: HeatmapSpec) -> bool:
    return bool(spec.zone_green or spec.zone_red)


def _espn_season_note(payload: dict[str, Any], phase: str) -> str:
    """Season stamp for points-table labels, parsed from ESPN's season display
    name - "2026-27" for cross-year leagues, "2026" for calendar leagues like
    the Brasileirão. `phase` is "season" (a reset table) or "final" (last
    season's completed table)."""
    display = str((payload.get("season") or {}).get("displayName") or "")
    match = re.match(r"(\d{4})(?:-(\d{2}))?", display)
    if not match:
        return ""
    if match.group(2):
        return f" · {int(match.group(1)) % 100:02d}/{match.group(2)} {phase}"
    return f" · {match.group(1)} {phase}"


def _espn_groups(payload: dict[str, Any]) -> list[list[dict[str, Any]]]:
    groups: list[list[dict[str, Any]]] = [
        (group.get("standings") or {}).get("entries") or []
        for group in payload.get("children") or []
    ]
    groups = [entries for entries in groups if entries]
    if not groups:
        groups = [(payload.get("standings") or {}).get("entries") or []]
    return groups


def _espn_played_any(groups: list[list[dict[str, Any]]]) -> bool:
    for entries in groups:
        for entry in entries:
            for stat in entry.get("stats") or []:
                if (
                    stat.get("name") == "gamesPlayed"
                    and int(stat.get("value") or 0) > 0
                ):
                    return True
    return False


async def _fetch_espn_tiles(spec: HeatmapSpec) -> list[dict[str, Any]]:
    """Big-4 standings as tiles: area by wins (or table points), color by the
    competition's qualification zones when the spec declares them (playoff
    seats green, drop zone red - computed per conference/league group),
    otherwise by the current streak. ESPN's public standings JSON is
    keyless."""
    payload = await fetch_json(
        f"{_ESPN_STANDINGS_URL}/{spec.code}/standings", headers=_ESPN_HEADERS
    )
    season_note = ""
    # Pre-season honesty, readable edition: an all-zero points table is the
    # NEW season's reset - a wall of "0 pts" tells the reader nothing, so
    # serve LAST season's final table from ESPN's archive, stamped "· 25/26
    # final". If the archive is missing, keep the reset table stamped with
    # the new season instead.
    if spec.table and not _espn_played_any(_espn_groups(payload)):
        year = int((payload.get("season") or {}).get("year") or 0)
        if year:
            try:
                prev = await fetch_json(
                    f"{_ESPN_STANDINGS_URL}/{spec.code}/standings",
                    headers=_ESPN_HEADERS,
                    params={"season": year - 1},
                )
            except NewsFetchError:
                prev = None
            if prev and _espn_played_any(_espn_groups(prev)):
                payload = prev
                season_note = _espn_season_note(prev, "final")
        if not season_note:
            season_note = _espn_season_note(payload, "season")
    groups = _espn_groups(payload)
    tiles: list[dict[str, Any]] = []
    for entries in groups:
        rows: list[dict[str, Any]] = []
        for entry in entries:
            team = entry.get("team") or {}
            name = str(team.get("displayName") or "")
            symbol = str(team.get("abbreviation") or name[:3].upper())
            stats = {
                str(s.get("name")): s for s in entry.get("stats") or [] if s.get("name")
            }
            wins = int((stats.get("wins") or {}).get("value") or 0)
            losses = int((stats.get("losses") or {}).get("value") or 0)
            if not name:
                continue
            # Big-4 standings carry a `streak` (±games); soccer leagues carry
            # `rankChange` (positions climbed) instead - both natural heat.
            if "streak" in stats:
                streak_heat = float((stats.get("streak") or {}).get("value") or 0.0)
            else:
                streak_heat = float((stats.get("rankChange") or {}).get("value") or 0.0)
            # Points-table sports size by points; win-loss sports by wins.
            if spec.table:
                points = int((stats.get("points") or {}).get("value") or 0)
                weight = float(max(points, 1))
                label = f"{points} pts"
                price = float(points)
            else:
                weight = float(wins + 1)
                label = f"{wins}-{losses}"
                price = float(wins)
            links = team.get("links") or []
            url = str(links[0].get("href")) if links and links[0].get("href") else None
            logos = team.get("logos") or []
            logo = str(logos[0].get("href")) if logos and logos[0].get("href") else None
            rows.append(
                {
                    "symbol": symbol,
                    "name": name,
                    "logo": logo,
                    "changePercent": round(max(-3.0, min(streak_heat, 3.0)), 2),
                    "price": price,
                    "weight": weight,
                    "label": label,
                    "url": url,
                    # gamesPlayed where the league provides it (rugby tables
                    # carry no wins/losses stats, which read as 0-0 forever).
                    "_played": int((stats.get("gamesPlayed") or {}).get("value") or 0)
                    or wins + losses,
                }
            )
        # Zones (or streak remnants) only mean something once the season is
        # genuinely underway - until at least half the group has played,
        # standings order is alphabetical accident (one Hall-of-Fame preseason
        # game made "top 7" = ARI/ATL/CHI/DAL/DET/GB), and ESPN keeps last
        # season's streak values on 0-0 rows.
        played_count = sum(1 for row in rows if row["_played"] > 0)
        if season_note:
            for row in rows:
                row["label"] += season_note
        if played_count * 2 < len(rows):
            for row in rows:
                row["changePercent"] = 0.0
        elif _has_zones(spec):
            # Seats within the group follow the sized metric (points/wins) -
            # the same order the treemap ranks the tiles.
            rows.sort(key=lambda row: (-row["weight"], row["name"]))
            for seat, row in enumerate(rows, start=1):
                row["changePercent"] = _zone_heat(spec, seat, len(rows))
        for row in rows:
            del row["_played"]
        tiles.extend(rows)
    return tiles


async def _fetch_espn_rankings_tiles(spec: HeatmapSpec) -> list[dict[str, Any]]:
    """Poll/ranking grids (CFB Top 25, ATP/WTA): tiles sized by poll or
    ranking points, colored by places moved since last week, labelled with the
    rank. Works for team polls (`team`) and athlete rankings (`athlete`)."""
    payload = await fetch_json(
        f"{_ESPN_SITE_URL}/{spec.code}/rankings", headers=_ESPN_HEADERS
    )
    rankings = payload.get("rankings") or []
    ranks = (rankings[0] if rankings else {}).get("ranks") or []
    tiles: list[dict[str, Any]] = []
    for entry in ranks[:25]:
        team = entry.get("team") or {}
        athlete = entry.get("athlete") or {}
        name = str(
            team.get("nickname")
            or team.get("displayName")
            or athlete.get("displayName")
            or ""
        )
        symbol = str(team.get("abbreviation") or athlete.get("shortName") or name[:12])
        if not name:
            continue
        current = int(entry.get("current") or 0)
        points = float(entry.get("points") or 0.0)
        trend_raw = str(entry.get("trend") or "").strip()
        try:
            # "+3" climbed, "-2" dropped, "-" unchanged.
            trend = float(trend_raw)
        except ValueError:
            trend = 0.0
        # Team polls carry a plain `logo` url; athlete rankings a `headshot`
        # (string or {href}).
        headshot = athlete.get("headshot")
        logo = (
            str(team.get("logo") or "")
            or (
                str(headshot.get("href") or "")
                if isinstance(headshot, dict)
                else str(headshot or "")
            )
        ) or None
        tiles.append(
            {
                "symbol": symbol,
                "name": name,
                "logo": logo,
                "changePercent": round(max(-3.0, min(trend, 3.0)), 2),
                "price": float(current),
                "weight": max(points, 1.0),
                "label": f"#{current}",
                "url": f"https://news.google.com/search?q={quote_plus(name)}",
            }
        )
    return tiles


async def _fetch_espn_mma_tiles(spec: HeatmapSpec) -> list[dict[str, Any]]:
    """The nearest event's fight card as equal tiles: live fights burn green,
    finished ones sit faint with the winner marked, upcoming ones neutral."""
    payload = await fetch_json(
        f"{_ESPN_SITE_URL}/{spec.code}/scoreboard", headers=_ESPN_HEADERS
    )
    events = payload.get("events") or []
    if not events:
        return []
    event = events[0]
    tiles: list[dict[str, Any]] = []
    for bout in (event.get("competitions") or [])[:16]:
        competitors = bout.get("competitors") or []
        names = [
            str(((c.get("athlete") or {}).get("shortName")) or "")
            for c in competitors[:2]
        ]
        if len(names) < 2 or not all(names):
            continue
        status = bout.get("status") or {}
        state = str((status.get("type") or {}).get("state") or "")
        completed = bool((status.get("type") or {}).get("completed"))
        winner = next(
            (
                str(((c.get("athlete") or {}).get("shortName")) or "")
                for c in competitors
                if c.get("winner")
            ),
            None,
        )
        heat = 3.0 if state == "in" else 0.5 if completed else -0.5
        label = (
            f"{winner} won"
            if winner
            else str((status.get("type") or {}).get("shortDetail") or "")[:26]
        )
        tiles.append(
            {
                "symbol": f"{names[0]} v {names[1]}",
                "name": str(event.get("name") or ""),
                "changePercent": heat,
                "price": 0.0,
                "weight": 1.0,
                "label": label,
                "url": (
                    "https://news.google.com/search?"
                    f"q={quote_plus(f'{names[0]} vs {names[1]}')}"
                ),
            }
        )
    return tiles


_BUZZ_FRESH_MS = 7 * 24 * 60 * 60 * 1000


def buzz_family(spec: HeatmapSpec) -> list[tuple[str, str, str | None]]:
    """(source_id, display name, logo) triples for a buzz map's entity family,
    selected by `spec.code`'s comma-list of source-id prefixes (e.g. city
    feeds). Shared between the tile builder and the background warmer so both
    agree on exactly which feeds constitute a map."""
    # Function-level import ON PURPOSE: metadata imports this module to build
    # the roster, so a top-level import back at metadata would be circular. By
    # the time a request reaches this fetcher both modules are fully loaded.
    from .metadata import SOURCES

    prefixes = tuple(p for p in spec.code.split(",") if p)
    family: list[tuple[str, str, str | None]] = []
    for source_id, meta in SOURCES.items():
        # The "-new" vertical cards (movie-new, tv-new, …) are curated release
        # feeds, not entities - they'd dominate every buzz map as one always-
        # fresh mega-tile.
        if not source_id.startswith(prefixes) or source_id.endswith("-new"):
            continue
        name = str(meta.get("name") or source_id)
        # The per-country Top Stories feeds all share one name; their distinct
        # label (the country) lives in `title` - without this the World Buzz
        # map renders every tile as "Top Stories".
        if name == "Top Stories":
            name = str(meta.get("title") or name)
        logo = str(meta.get("logo") or "") or None
        family.append((source_id, name, logo))
    return family


async def demanded_buzz_ids(redis: Redis) -> list[str]:
    """Buzz map ids someone viewed within the demand window."""
    buzz_ids = [hid for hid, spec in HEATMAPS.items() if spec.provider == "buzz"]
    flags = await redis.mget([_DEMAND_KEY.format(id=hid) for hid in buzz_ids])
    return [hid for hid, flag in zip(buzz_ids, flags, strict=True) if flag]


async def _fetch_buzz_tiles(redis: Redis, spec: HeatmapSpec) -> list[dict[str, Any]]:
    """News-volume tiles from feeds already cached on the wall (no external
    calls): area by story count in the last 7 days, color by how fresh the
    latest story is (older than two days reads faint, not absent)."""
    family = buzz_family(spec)
    if not family:
        return []
    # Chunk the MGETs: the topics family is 500+ ids and one giant MGET would
    # sit on Redis' hot path (search.py uses the same 250 bound).
    ids = [source_id for source_id, _, _ in family]
    raws: list[tuple[str, str | bytes | None]] = []
    for start in range(0, len(ids), 250):
        raws.extend(await mget_hot_raw(redis, ids[start : start + 250]))
    names = {source_id: name for source_id, name, _ in family}
    logos = {source_id: logo for source_id, _, logo in family}
    now = now_ms()
    tiles: list[dict[str, Any]] = []
    for source_id, raw in raws:
        entry = parse_entry(raw)
        if entry is None:
            continue
        dates = [item.pub_date for item in entry.items if item.pub_date]
        fresh = sum(1 for ms in dates if now - ms < _BUZZ_FRESH_MS)
        if fresh == 0:
            continue
        newest_hours = (now - max(dates)) / 3_600_000 if dates else 999.0
        # Old-but-within-a-week reads neutral (the clients' zero color), not
        # negative - "quiet" isn't "down" on a buzz map.
        heat = (
            3.0
            if newest_hours < 6
            else 1.5
            if newest_hours < 24
            else 0.5
            if newest_hours < 48
            else 0.0
        )
        name = names[source_id]
        short = name
        if spec.strip:
            short = short.removeprefix(spec.strip).strip() or short
        tiles.append(
            {
                "symbol": short[:14],
                "name": name,
                "logo": logos.get(source_id),
                "changePercent": heat,
                "price": float(fresh),
                "weight": float(fresh),
                "label": f"{fresh} " + ("story" if fresh == 1 else "stories"),
                "url": f"https://news.google.com/search?q={quote_plus(name)}",
            }
        )
    # One or two cached feeds is not real coverage of the family - a map built
    # from them is a single mega-tile ("DUBLIN, 9 stories" filling the card).
    # Fail the build instead, so the card drops off the wall until the warmer
    # has the family cached.
    if len(tiles) < 3:
        return []
    tiles.sort(key=lambda tile: tile["weight"], reverse=True)
    return tiles[:28]


async def _fetch_cricket_tiles() -> list[dict[str, Any]]:
    """Live and recent cricket matches as an equal-tile grid: a live game burns
    full green, a finished one sits faintly green with its result, an upcoming
    one faintly red with its start status. cricketdata.org free tier is
    100 req/day - the shared 5-minute cache keeps us far under it."""
    payload = await fetch_json(
        _CRICKETDATA_URL,
        params={"apikey": settings.CRICKETDATA_API_KEY or "", "offset": 0},
    )
    tiles: list[dict[str, Any]] = []
    for match in (payload.get("data") or [])[:16]:
        teams = match.get("teamInfo") or []
        shorts = [str(t.get("shortname") or "")[:4] for t in teams[:2]]
        if len(shorts) < 2 or not all(shorts):
            names = match.get("teams") or []
            shorts = [str(n)[:3].upper() for n in names[:2]]
        if len(shorts) < 2:
            continue
        started = bool(match.get("matchStarted"))
        ended = bool(match.get("matchEnded"))
        heat = 3.0 if started and not ended else 0.5 if ended else -0.5
        status = str(match.get("status") or "")
        match_name = str(match.get("name") or "")
        tiles.append(
            {
                "symbol": f"{shorts[0]} v {shorts[1]}",
                "name": match_name,
                "changePercent": heat,
                "price": 0.0,
                "weight": 1.0,
                "label": status if len(status) <= 26 else f"{status[:25]}…",
                "url": f"https://news.google.com/search?q={quote_plus(match_name)}"
                if match_name
                else None,
            }
        )
    return tiles


async def _fetch_f1_tiles() -> list[dict[str, Any]]:
    """Driver championship as tiles: area by season points, color by how the
    driver scored in the LAST race (a winner burns full green, a pointless
    finish reads faintly red), label = the points tally. Jolpica mirrors the
    retired Ergast API, keyless."""
    standings_payload = await fetch_json(f"{_F1_URL}/current/driverstandings.json")
    lists = ((standings_payload.get("MRData") or {}).get("StandingsTable") or {}).get(
        "StandingsLists"
    ) or []
    standings = (lists[0] if lists else {}).get("DriverStandings") or []
    last_points: dict[str, float] = {}
    try:
        last_payload = await fetch_json(f"{_F1_URL}/current/last/results.json")
        races = ((last_payload.get("MRData") or {}).get("RaceTable") or {}).get(
            "Races"
        ) or []
        for result in (races[0] if races else {}).get("Results") or []:
            code = str((result.get("Driver") or {}).get("code") or "")
            if code:
                last_points[code] = float(result.get("points") or 0.0)
    except NewsFetchError:
        pass  # standings alone still make a map; tiles just read neutral
    tiles: list[dict[str, Any]] = []
    for row in standings:
        driver = row.get("Driver") or {}
        code = str(driver.get("code") or "")
        name = f"{driver.get('givenName', '')} {driver.get('familyName', '')}".strip()
        points = float(row.get("points") or 0.0)
        if not name:
            continue
        scored = last_points.get(code)
        # Clamp to ±3 like every other fetcher - sprint/fastest-lap bonuses can
        # push a single race past 25 points.
        heat = (
            0.0
            if scored is None
            else min((scored / 25.0) * 3.0, 3.0)
            if scored > 0
            else -0.6
        )
        tiles.append(
            {
                "symbol": code or name[:3].upper(),
                "name": name,
                "changePercent": round(heat, 2),
                "price": points,
                "weight": points + 1.0,
                "label": f"{points:g} pts",
                "url": str(driver.get("url")) if driver.get("url") else None,
            }
        )
    return tiles


# Strong references to in-flight background refreshes: a bare create_task is
# garbage-collectable mid-flight, which would silently kill the refresh.
_refresh_tasks: set[asyncio.Task[None]] = set()


async def _refresh_in_background(
    redis: Redis, heatmap_id: str, cached: dict[str, Any] | None
) -> None:
    """Run the blocking refetch path detached from the request that armed it,
    so a stale map serves instantly (stale-while-revalidate) while the new
    tiles land in cache for the next reader. The stale ``cached`` copy is
    threaded through so a failed refresh serves stale instead of arming the
    cold-failure marker while a servable map still exists."""
    try:
        await _fetch_and_store(redis, heatmap_id, cached=cached)
    except OutceptionError:
        # Cold-failure bookkeeping already happened inside; only reachable
        # with no stale copy to fall back on.
        pass
    except Exception as exc:
        log.info("news.heatmap_refresh_failed", heatmap_id=heatmap_id, error=str(exc))


async def get_heatmap(redis: Redis, heatmap_id: str) -> dict[str, Any]:
    """Tiles for one heatmap, cache-first with serve-stale-on-error. A stale
    (but present) map serves immediately and refreshes in the background -
    only a cold cache makes the reader wait on the upstream."""
    spec = HEATMAPS.get(heatmap_id)
    if spec is None or heatmap_id not in available_heatmap_ids():
        raise OutceptionError("Unknown heatmap", status_code=404)

    if spec.provider == "buzz":
        await redis.set(_DEMAND_KEY.format(id=heatmap_id), "1", ex=_DEMAND_TTL_SECONDS)

    key = _CACHE_KEY.format(id=heatmap_id)
    cached_raw = await redis.get(key)
    cached: dict[str, Any] | None = None
    if cached_raw is not None:
        try:
            parsed = json.loads(cached_raw)
            # Guard the timestamp read too: a malformed/legacy payload (e.g. a
            # bare list) must be a miss, not an unhandled TypeError.
            if isinstance(parsed, dict) and "updatedTime" in parsed:
                cached = parsed
        except ValueError:
            cached = None
    if cached is not None:
        try:
            fresh = now_ms() - int(cached["updatedTime"]) < spec.interval_ms
        except (TypeError, ValueError):
            fresh = False
        if fresh:
            return {**cached, "status": "success"}
        # Stale-while-revalidate: hand the reader the stale tiles NOW and let
        # the single-flight winner refresh detached from this request. The
        # cooldown key both elects the winner and stops re-arming stampedes.
        won = await redis.set(
            _REFETCH_KEY.format(id=heatmap_id),
            "1",
            ex=_REFETCH_COOLDOWN_SECONDS,
            nx=True,
        )
        if won:
            task = asyncio.create_task(
                _refresh_in_background(redis, heatmap_id, cached)
            )
            _refresh_tasks.add(task)
            task.add_done_callback(_refresh_tasks.discard)
        return {**cached, "status": "cache"}

    # Cold cache: the reader has nothing to look at, so the fetch happens
    # inline. Single-flight - only the winner hits the upstream; losers are
    # told to retry shortly. A recent cold failure short-circuits so a dead
    # upstream can't be hammered.
    won = await redis.set(
        _REFETCH_KEY.format(id=heatmap_id),
        "1",
        ex=_REFETCH_COOLDOWN_SECONDS,
        nx=True,
    )
    if not won:
        raise OutceptionError("Heatmap is warming up", status_code=503)
    if await redis.get(_FAIL_KEY.format(id=heatmap_id)):
        raise OutceptionError("Heatmap is unavailable", status_code=502)
    return await _fetch_and_store(redis, heatmap_id, cached=None)


async def _fetch_and_store(
    redis: Redis, heatmap_id: str, cached: dict[str, Any] | None
) -> dict[str, Any]:
    spec = HEATMAPS[heatmap_id]
    key = _CACHE_KEY.format(id=heatmap_id)
    try:
        if spec.provider == "coingecko":
            tiles = await _fetch_coingecko_tiles()
        elif spec.provider == "frankfurter":
            tiles = await _fetch_frankfurter_tiles()
        elif spec.provider == "steam":
            tiles = await _fetch_steam_tiles(redis)
        elif spec.provider == "espn":
            tiles = await _fetch_espn_tiles(spec)
        elif spec.provider == "espn-rankings":
            tiles = await _fetch_espn_rankings_tiles(spec)
        elif spec.provider == "espn-mma":
            tiles = await _fetch_espn_mma_tiles(spec)
        elif spec.provider == "buzz":
            tiles = await _fetch_buzz_tiles(redis, spec)
        elif spec.provider == "cricket":
            tiles = await _fetch_cricket_tiles()
        elif spec.provider == "f1":
            tiles = await _fetch_f1_tiles()
        else:
            tiles = await _fetch_finnhub_tiles(redis, spec)
        if not tiles:
            raise NewsFetchError("empty heatmap")
        # A partial fetch (e.g. half the quotes 429'd mid-storm) must not be
        # cached as an authoritative map, replacing a complete stale one. Only
        # the symbol-based (finnhub) maps have a known target size.
        if spec.symbols and len(tiles) < len(spec.symbols) // 2:
            raise NewsFetchError(f"partial heatmap ({len(tiles)}/{len(spec.symbols)})")
        # Drop only true dust (< 0.1% of the map). The clients lay areas out
        # with square-root-dampened weights, so everything above this renders
        # as a readable tile rather than a sliver. After the partial guard on
        # purpose, so filtering can't fake a "half the quotes died" signal.
        total_weight = sum(tile["weight"] for tile in tiles)
        if total_weight > 0:
            tiles = [tile for tile in tiles if tile["weight"] >= total_weight * 0.001]
        # Sports grids read as uniform rosters, not market caps: every team
        # the same size, in standings order (the fetchers emit that order and
        # the clients' stable sort preserves it for equal weights). Color
        # already carries the standings signal (qualification zones).
        if spec.column == "sports":
            for tile in tiles:
                tile["weight"] = 1.0
    # Broad, like _get_source: third-party JSON coercion (int()/float() over
    # ESPN "-" placeholders, missing keys) can raise beyond NewsFetchError, and
    # every such surprise must serve stale rather than 500 + page Sentry.
    except Exception as exc:
        if cached is not None:
            return {**cached, "status": "cache"}
        # Remember the cold failure briefly so retries don't stampede the dead
        # upstream (finnhub key at 429, cricket quota burned, …).
        await redis.set(_FAIL_KEY.format(id=heatmap_id), "1", ex=_FAIL_COOLDOWN_SECONDS)
        log.info("news.heatmap_failed", heatmap_id=heatmap_id, error=str(exc))
        raise OutceptionError("Heatmap is unavailable", status_code=502) from exc

    payload = {"id": heatmap_id, "updatedTime": now_ms(), "tiles": tiles}
    await redis.set(key, json.dumps(payload), ex=_HARD_TTL_SECONDS)
    return {**payload, "status": "success"}
