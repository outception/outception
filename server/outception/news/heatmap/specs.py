"""The table specs: one `HeatmapSpec` per table card, built from the
catalog's `tables.json` and `live_signals.json`, and the provider
declarations the toolkit reads (interval, freshness, budget, cooldown
range, byte cap, terms)."""

from dataclasses import dataclass

from outception.config import settings
from outception.net.provider import ProviderSpec

from ..catalog import catalog

HEATMAP_INTERVAL_MS = 5 * 60 * 1000
# The serve-stale window; well past a weekend gap.
HARD_TTL_SECONDS = 24 * 60 * 60


@dataclass(frozen=True)
class HeatmapSpec:
    name: str
    desc: str
    color: str
    # The provider module under `providers/` that builds the tiles.
    provider: str
    # (symbol, display name); symbol universes only
    symbols: tuple[tuple[str, str], ...] = ()
    # Roster column ("finance" for markets, "sports" for result grids)
    column: str = "finance"
    # Provider-specific selector: a standings path, a buzz family's id
    # prefixes, a transit agency.
    code: str = ""
    # Freshness window; rate-capped providers stretch it.
    interval_ms: int = HEATMAP_INTERVAL_MS
    # Standings only: points-table sports size tiles by table points,
    # win-loss sports by wins.
    table: bool = False
    # Standings qualification zones, checked against each competition's
    # rules: top `zone_green` qualify outright and burn green; the next
    # `zone_soft` are the softer band; the bottom `zone_red` are the drop
    # zone, preceded by `zone_red_soft`. All zero keeps the provider's own
    # heat (form or streak). For grouped standings zones apply per group.
    zone_green: int = 0
    zone_soft: int = 0
    zone_red: int = 0
    zone_red_soft: int = 0
    # Buzz maps over per-country families: leading phrase to strip from
    # source names so tiles read "Ireland", not "Property Irela…".
    strip: str = ""
    id: str = ""
    # Live signals only: off until the data says otherwise.
    enabled: bool = True
    live: bool = False


# How the toolkit treats each upstream: how often a table refreshes, how
# long a value is served stale, how many attempts a day, how a Retry-After
# is clamped. Keyless upstreams with a published rate get a budget.
PROVIDER_NET: dict[str, ProviderSpec] = {
    "finnhub": ProviderSpec(
        id="finnhub",
        interval=HEATMAP_INTERVAL_MS,
        fresh_for=HEATMAP_INTERVAL_MS,
        stale_for=HARD_TTL_SECONDS * 1000,
        cooldown_range=(30, 900),
        terms="Market data by Finnhub",
    ),
    "coingecko": ProviderSpec(
        id="coingecko",
        interval=HEATMAP_INTERVAL_MS,
        fresh_for=HEATMAP_INTERVAL_MS,
        stale_for=HARD_TTL_SECONDS * 1000,
        budget_per_day=2000,
        cooldown_range=(60, 900),
        terms="Crypto prices by CoinGecko",
    ),
    "frankfurter": ProviderSpec(
        id="frankfurter",
        interval=HEATMAP_INTERVAL_MS,
        fresh_for=HEATMAP_INTERVAL_MS,
        stale_for=HARD_TTL_SECONDS * 1000,
        cooldown_range=(60, 900),
        terms="Reference rates by the European Central Bank via Frankfurter",
    ),
    "steam": ProviderSpec(
        id="steam",
        interval=HEATMAP_INTERVAL_MS,
        fresh_for=HEATMAP_INTERVAL_MS,
        stale_for=HARD_TTL_SECONDS * 1000,
        cooldown_range=(60, 900),
        terms="Player counts from the Steam store",
    ),
    "espn": ProviderSpec(
        id="espn",
        interval=HEATMAP_INTERVAL_MS,
        fresh_for=HEATMAP_INTERVAL_MS,
        stale_for=HARD_TTL_SECONDS * 1000,
        cooldown_range=(60, 900),
        terms="Standings and rankings by ESPN",
    ),
    "cricket": ProviderSpec(
        id="cricket",
        interval=15 * 60 * 1000,
        fresh_for=15 * 60 * 1000,
        stale_for=HARD_TTL_SECONDS * 1000,
        budget_per_day=90,
        cooldown_range=(300, 3600),
        terms="Match data by CricketData.org",
    ),
    "f1": ProviderSpec(
        id="f1",
        interval=HEATMAP_INTERVAL_MS,
        fresh_for=HEATMAP_INTERVAL_MS,
        stale_for=HARD_TTL_SECONDS * 1000,
        cooldown_range=(60, 900),
        terms="Championship data by Jolpica, after Ergast",
    ),
    # Buzz maps read the wall cache; nothing upstream to cool down or budget.
    "buzz": ProviderSpec(
        id="buzz",
        interval=HEATMAP_INTERVAL_MS,
        fresh_for=HEATMAP_INTERVAL_MS,
        stale_for=HARD_TTL_SECONDS * 1000,
    ),
}

# The provider family behind each spec provider id (the sports network
# serves three table shapes from one upstream).
PROVIDER_FAMILY: dict[str, str] = {
    "espn-rankings": "espn",
    "espn-mma": "espn",
}

# Table providers that need a key: the table leaves the roster without it.
KEYED_PROVIDERS: dict[str, str] = {
    "finnhub": "FINNHUB_API_KEY",
    "cricket": "CRICKETDATA_API_KEY",
}


def net_spec(spec: HeatmapSpec) -> ProviderSpec:
    """The toolkit declaration for a table's upstream."""
    if spec.live:
        return LIVE_NET[spec.id]
    family = PROVIDER_FAMILY.get(spec.provider, spec.provider)
    base = PROVIDER_NET[family]
    if base.interval == spec.interval_ms:
        return base
    return ProviderSpec(
        id=base.id,
        interval=spec.interval_ms,
        fresh_for=spec.interval_ms,
        stale_for=base.stale_for,
        budget_per_day=base.budget_per_day,
        cooldown_range=base.cooldown_range,
        byte_cap=base.byte_cap,
        terms=base.terms,
    )


def _build() -> tuple[dict[str, HeatmapSpec], dict[str, ProviderSpec]]:
    data = catalog()
    specs: dict[str, HeatmapSpec] = {}
    for row in data.tables:
        specs[row.id] = HeatmapSpec(
            name=row.name,
            desc=row.desc,
            color=row.color,
            provider=row.provider,
            symbols=tuple((symbol, name) for symbol, name in row.symbols),
            column=row.column,
            code=row.code,
            interval_ms=row.interval_ms,
            table=row.table,
            zone_green=row.zone_green,
            zone_soft=row.zone_soft,
            zone_red=row.zone_red,
            zone_red_soft=row.zone_red_soft,
            strip=row.strip,
            id=row.id,
        )
    live: dict[str, ProviderSpec] = {}
    by_id = data.by_id
    for signal in data.live_signals:
        roster = by_id[signal.id]
        specs[signal.id] = HeatmapSpec(
            name=signal.name,
            desc=roster.desc or "",
            color=roster.color,
            provider=signal.provider,
            column=roster.column or "science",
            code=signal.code,
            interval_ms=signal.interval,
            id=signal.id,
            enabled=signal.enabled,
            live=True,
        )
        live[signal.id] = ProviderSpec(
            id=signal.id,
            interval=signal.interval,
            fresh_for=signal.fresh_for,
            stale_for=signal.stale_for,
            budget_per_day=signal.budget_per_day,
            cooldown_range=signal.cooldown_range,
            byte_cap=signal.byte_cap,
            terms=signal.terms,
        )
    return specs, live


HEATMAPS, LIVE_NET = _build()


def is_configured(spec: HeatmapSpec) -> bool:
    """Whether the table can be served with the current configuration: a
    keyed provider needs its key, a live signal needs to be switched on."""
    if spec.live:
        return spec.enabled
    field = KEYED_PROVIDERS.get(spec.provider)
    return bool(getattr(settings, field)) if field else True


def available_heatmap_ids() -> list[str]:
    return [heatmap_id for heatmap_id, spec in HEATMAPS.items() if is_configured(spec)]
