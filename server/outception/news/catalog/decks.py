"""The catalog's deck data in the composer's shape, and the two per-country
compositions the routes serve: the default deck and the Starters."""

from typing import TypedDict

from outception.cards.deck import (
    DeckData,
    DeckEntry,
    DeckInput,
    compose_default_deck,
    resolve,
)

from .registry import Registry

_DECK_DATA: dict[int, DeckData] = {}


def deck_data(registry: Registry) -> DeckData:
    """The composer's view of the catalog, built once per registry."""
    cached = _DECK_DATA.get(id(registry))
    if cached is not None:
        return cached
    deck = registry.catalog.deck
    data = DeckData(
        base=tuple(
            DeckEntry(
                entry.id,
                inject_after=tuple(entry.inject_after),
                swap=entry.swap,
                enabled=entry.enabled,
                season=entry.season,
                countries=frozenset(entry.countries) if entry.countries else None,
            )
            for entry in deck.base
        ),
        country_tables=registry.catalog.country_tables,
    )
    _DECK_DATA[id(registry)] = data
    return data


class ResolvedTemplate(TypedDict):
    id: str
    sources: list[str]


def default_cards(
    registry: Registry,
    country: str | None,
    *,
    month: int,
    shared_card: str | None = None,
) -> list[str]:
    inp = DeckInput(
        country=country,
        month=month,
        known=registry.is_known,
        disabled=registry.is_disabled,
        shared_card=shared_card,
    )
    return compose_default_deck(deck_data(registry), inp)


def resolve_templates(
    registry: Registry, country: str | None
) -> list[ResolvedTemplate]:
    """The Starters for a country: each template's fixed sources plus its
    country-resolved extras, deduped, unknown and disabled ids dropped, empty
    templates left out."""
    data = deck_data(registry)
    out: list[ResolvedTemplate] = []
    for template in registry.catalog.templates:
        ids = list(template.sources)
        for ref in template.extras:
            ids.extend(resolve(ref, data, country))
        seen: set[str] = set()
        sources: list[str] = []
        for sid in ids:
            if sid in seen or not registry.is_known(sid) or registry.is_disabled(sid):
                continue
            seen.add(sid)
            sources.append(sid)
        if sources:
            out.append({"id": template.id, "sources": sources})
    return out
