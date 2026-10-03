"""The deck composer: an ordered list of card ids for one reader.

The server composes only the default deck, seeded by country and city from
`news/data/decks/default.json` and the country tables; it is edge-cached
for an hour, so it stays free of the briefing and shared-card splices,
which are client deck rules in `news-core`. The precedence rule, written
down once and mirrored there:

1. the shared card when present, else the country card
2. the briefing card for the reader's profile
3. the rest in catalog order
4. dedupe; drop unknown, disabled and `fallback` ids; cap

This module holds the pure composition over data already loaded. The data
files arrive with the news domain; until then the composer works on the
`DeckData` it is given, and the parity fixtures under
`tests/news/fixtures/parity` are the contract it must reproduce.
"""

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field

from .kinds import WEATHER_STRIP_ID, briefing_card_id

DECK_CAP = 120


@dataclass(frozen=True)
class DeckEntry:
    """One entry of the ordered base list. `inject_after` names the ids
    spliced right after this entry, resolved per country; `swap` names the
    country table that replaces the entry when the country has one."""

    id: str
    inject_after: tuple[str, ...] = ()
    swap: str | None = None
    enabled: bool = True
    season: tuple[int, int] | None = None  # month range, inclusive
    countries: frozenset[str] | None = None


@dataclass(frozen=True)
class DeckData:
    base: tuple[DeckEntry, ...]
    # country code -> table name -> ids
    country_tables: dict[str, dict[str, tuple[str, ...]]] = field(default_factory=dict)
    briefing_profile_by_country: dict[str, str] = field(default_factory=dict)
    default_briefing_profile: str = "news-junkie"


@dataclass(frozen=True)
class DeckInput:
    country: str | None
    month: int
    known: Callable[[str], bool]
    disabled: Callable[[str], bool]
    fallback: Callable[[str], bool] = lambda _: False
    shared_card: str | None = None
    briefing_enabled: bool = False


def _country_table(data: DeckData, country: str | None, name: str) -> tuple[str, ...]:
    if country is None:
        return ()
    return data.country_tables.get(country, {}).get(name, ())


def _entry_applies(entry: DeckEntry, inp: DeckInput) -> bool:
    if not entry.enabled:
        return False
    if entry.season is not None:
        start, end = entry.season
        inside = (
            start <= inp.month <= end if start <= end else not (end < inp.month < start)
        )
        if not inside:
            return False
    return entry.countries is None or (
        inp.country is not None and inp.country in entry.countries
    )


def resolve(ref: str, data: DeckData, country: str | None) -> tuple[str, ...]:
    """An injected ref is a literal id or `country:<table>`, which resolves
    to the country's table (empty when the country has none)."""
    if ref.startswith("country:"):
        return _country_table(data, country, ref[len("country:") :])
    return (ref,)


def compose_default_deck(data: DeckData, inp: DeckInput) -> list[str]:
    """The default deck for a visitor: country card first, then the ordered
    base list with its country injections and swaps, deduped, filtered, the
    weather strip id last."""
    cards: list[str] = []
    if inp.shared_card:
        cards.append(inp.shared_card)
    if inp.country:
        cards.append(f"gnews-{inp.country.lower()}")
    if inp.briefing_enabled:
        profile = data.briefing_profile_by_country.get(
            inp.country or "", data.default_briefing_profile
        )
        cards.append(briefing_card_id(profile))
    for entry in data.base:
        if not _entry_applies(entry, inp):
            continue
        swapped = _country_table(data, inp.country, entry.swap) if entry.swap else ()
        if swapped:
            cards.extend(swapped)
        else:
            cards.append(entry.id)
        for ref in entry.inject_after:
            cards.extend(resolve(ref, data, inp.country))
    return finalize(cards, inp)


def finalize(cards: Iterable[str], inp: DeckInput) -> list[str]:
    """Dedupe, drop unknown, disabled and fallback ids, pin the weather strip
    last, cap."""
    seen: set[str] = set()
    out: list[str] = []
    for card_id in cards:
        if card_id in seen:
            continue
        seen.add(card_id)
        if card_id == WEATHER_STRIP_ID or card_id.startswith("briefing:"):
            out.append(card_id)
            continue
        if not inp.known(card_id) or inp.disabled(card_id) or inp.fallback(card_id):
            continue
        out.append(card_id)
    has_weather = WEATHER_STRIP_ID in out
    content = [card_id for card_id in out if card_id != WEATHER_STRIP_ID][:DECK_CAP]
    if has_weather:
        content.append(WEATHER_STRIP_ID)
    return content


def always_warm_ids(
    ordered_sources: Sequence[str], default_cards: Iterable[str], head: int = 300
) -> list[str]:
    """The head of the ordered sources plus the default cards: what the
    warmer keeps fresh regardless of demand."""
    seen: set[str] = set()
    out: list[str] = []
    for card_id in [*ordered_sources[:head], *default_cards]:
        if (
            card_id in seen
            or card_id == WEATHER_STRIP_ID
            or card_id.startswith("briefing:")
        ):
            continue
        seen.add(card_id)
        out.append(card_id)
    return out
