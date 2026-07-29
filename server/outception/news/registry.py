"""Registry mapping source ids to their async getters.

Scraper modules call ``register()`` at import time (the ``sources``
package imports every module), mirroring the upstream glob-import
mechanism. A request can only ever reach a registered getter — there is
no path from user input to an arbitrary URL.
"""

from collections.abc import Awaitable, Callable

from .cache import DEFAULT_INTERVAL_MS
from .metadata import SOURCES
from .schemas import NewsItem

# Sources confirmed to consistently fail (dead feeds, paywalls, or upstreams
# that block/timeout this server). Hidden from the wall so no broken cards show.
DISABLED_SOURCES: frozenset[str] = frozenset(
    {
        # 2026-08-16 audit: dead/blocked from the prod host (502 twice through
        # the live API, 2 minutes apart), though some load from other networks.
        "almasryalyoum",
        "artnet",
        "arxiv_cs",
        "asharqalawsat",
        "benzinga",
        "birminghammail",
        "bruegel",
        "businessoffashion",
        "citizen_za",
        "colombiaone",
        "dailypost_ng",
        "dnevnik_bg",
        "elpais_uy",
        "ethiopianreporter",
        "fiercebiotech",
        "fiercepharma",
        "flightglobal",
        "heraldscotland",
        "holidaypirates",
        "hotelmanagement",
        "ilgiornale",
        "legit_ng",
        "liverpoolecho",
        "marketingweek",
        "marktechpost",
        "michaelwest",
        "moneyweb",
        "newzimbabwe",
        "nola",
        "philstar",
        "phys_arxiv",
        "quartz",
        "reliefweb",
        "rp_pl",
        "santiagotimes",
        "scontomaggio",
        "tennisworldusa",
        "the19th",
        "theafricareport",
        "thehindu",
        "themanchester",
        "thenational_scot",
        "thetruthaboutcars",
        "torontostar",
        "travelpirates",
        "tuko",
        "walesonline",
        # Pre-audit disables.
        "9news_au",
        "9to5linux",
        "actucameroun",
        "arabnews",
        "bangkokpost",
        "bostonglobe",
        "cbssports",
        "cnbc",
        "destructoid",
        "dotesports",
        "fin24",
        "fxstreet",
        "gothamist",
        "greekreporter",
        "guardianng",
        "herald_zw",
        "houstonchronicle",
        "hypebeast",
        "jamaicaobserver",
        "japantoday",
        "jeuneafrique",
        "kotaku",
        "mailguardian",
        "mg_africa",
        "news24_za2",
        "peruviantimes",
        "politico",
        "rte_ie",
        "seattletimes",
        "seattletimes2",
        "siliconera",
        "sportskeeda",
        "stuttgarter",
        "terra_br",
        "theatlantic",
        "thedefiant",
        "theinformation",
        "timesofisrael",
        "tmz",
        "tvn24",
        "udn",
        "ukroads",
        "youtube-lalalifegames",
    }
)

Getter = Callable[[], Awaitable[list[NewsItem]]]

GETTERS: dict[str, Getter] = {}


def register(source_id: str, getter: Getter) -> None:
    GETTERS[source_id] = getter


def source(source_id: str) -> Callable[[Getter], Getter]:
    """Decorator form: ``@source("hackernews")``."""

    def wrap(getter: Getter) -> Getter:
        register(source_id, getter)
        return getter

    return wrap


def resolve(source_id: str) -> str | None:
    """Follow a redirect alias to the canonical id. Returns None when the
    id is unknown or has no registered getter."""
    meta = SOURCES.get(source_id)
    if meta is None:
        return None
    redirect = meta.get("redirect")
    if redirect:
        source_id = redirect
    if source_id not in SOURCES or source_id not in GETTERS:
        return None
    return source_id


def interval_ms(source_id: str) -> int:
    return SOURCES.get(source_id, {}).get("interval", DEFAULT_INTERVAL_MS)
