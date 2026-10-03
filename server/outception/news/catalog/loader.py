"""Load and validate the catalog from `news/data/*.json`.

The loader checks that every id referenced anywhere resolves (redirects,
disabled rows, Starter rosters and extras, deck entries, country tables),
that columns are known and ids unique, and that every source names an
adapter unless it is a table. A broken catalog fails the build, never a
request.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from .schemas import (
    COLUMN_ORDER,
    CountryTablesFile,
    CreditRow,
    DeckFile,
    DisabledRow,
    LiveSignalRow,
    SourceRow,
    TemplateRow,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

_sources_adapter = TypeAdapter(list[SourceRow])
_disabled_adapter = TypeAdapter(list[DisabledRow])
_templates_adapter = TypeAdapter(list[TemplateRow])
_signals_adapter = TypeAdapter(list[LiveSignalRow])
_credits_adapter = TypeAdapter(list[CreditRow])


class CatalogError(ValueError):
    """The catalog does not hold together."""


@dataclass(frozen=True)
class Catalog:
    sources: tuple[SourceRow, ...]
    disabled: dict[str, DisabledRow]
    templates: tuple[TemplateRow, ...]
    live_signals: tuple[LiveSignalRow, ...]
    credits: tuple[CreditRow, ...]
    deck: DeckFile
    country_tables: dict[str, dict[str, tuple[str, ...]]] = field(default_factory=dict)

    @property
    def by_id(self) -> dict[str, SourceRow]:
        return {row.id: row for row in self.sources}

    def is_known(self, source_id: str) -> bool:
        return source_id in self.by_id

    def is_disabled(self, source_id: str) -> bool:
        return source_id in self.disabled

    def ordered(self) -> list[SourceRow]:
        """Registration order, stable-sorted by column rank, disabled rows
        excluded: the order the sources route serves and the warmer reads."""
        return sorted(
            (row for row in self.sources if row.id not in self.disabled),
            key=lambda row: COLUMN_ORDER.get(row.column or "", len(COLUMN_ORDER)),
        )


def _read(path: Path, default: str) -> object:
    if not path.exists():
        return json.loads(default)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise CatalogError(f"{path.name}: {e}") from e


def _validate[T](adapter: TypeAdapter[T], raw: object, name: str) -> T:
    try:
        return adapter.validate_python(raw)
    except ValidationError as e:
        raise CatalogError(f"{name}: {e}") from e


def load_catalog(data_dir: Path = DATA_DIR) -> Catalog:
    sources = _validate(
        _sources_adapter, _read(data_dir / "sources.json", "[]"), "sources.json"
    )
    disabled = _validate(
        _disabled_adapter, _read(data_dir / "disabled.json", "[]"), "disabled.json"
    )
    templates = _validate(
        _templates_adapter, _read(data_dir / "templates.json", "[]"), "templates.json"
    )
    signals = _validate(
        _signals_adapter,
        _read(data_dir / "live_signals.json", "[]"),
        "live_signals.json",
    )
    credits = _validate(
        _credits_adapter, _read(data_dir / "credits.json", "[]"), "credits.json"
    )
    deck = _validate(
        TypeAdapter(DeckFile),
        _read(data_dir / "decks" / "default.json", '{"base": []}'),
        "decks/default.json",
    )

    country_tables: dict[str, dict[str, tuple[str, ...]]] = {}
    country_dir = data_dir / "country"
    if country_dir.exists():
        for path in sorted(country_dir.glob("*.json")):
            table_file = _validate(
                TypeAdapter(CountryTablesFile),
                _read(path, "{}"),
                f"country/{path.name}",
            )
            for country, ids in table_file.entries.items():
                country_tables.setdefault(country.upper(), {})[table_file.table] = (
                    tuple(ids)
                )

    catalog = Catalog(
        sources=tuple(sources),
        disabled={row.id: row for row in disabled},
        templates=tuple(templates),
        live_signals=tuple(signals),
        credits=tuple(credits),
        deck=deck,
        country_tables=country_tables,
    )
    _check(catalog)
    return catalog


def _check(catalog: Catalog) -> None:
    problems: list[str] = []
    seen: set[str] = set()
    for row in catalog.sources:
        if row.id in seen:
            problems.append(f"duplicate source id {row.id}")
        seen.add(row.id)
        if row.column is not None and row.column not in COLUMN_ORDER:
            problems.append(f"{row.id}: unknown column {row.column}")
        if row.redirect is not None and row.redirect not in {
            r.id for r in catalog.sources
        }:
            problems.append(f"{row.id}: redirect to unknown id {row.redirect}")
        if row.type != "heatmap" and row.redirect is None and row.adapter is None:
            problems.append(f"{row.id}: no adapter and not a table")
    known = seen | {signal.id for signal in catalog.live_signals}
    for signal in catalog.live_signals:
        if signal.id in seen:
            problems.append(f"live signal {signal.id} collides with a source id")
    for disabled_id in catalog.disabled:
        if disabled_id not in known:
            problems.append(f"disabled.json names unknown id {disabled_id}")
    table_names = {
        name for tables in catalog.country_tables.values() for name in tables
    }
    for tables in catalog.country_tables.values():
        for name, ids in tables.items():
            for source_id in ids:
                if source_id not in known:
                    problems.append(
                        f"country table {name} names unknown id {source_id}"
                    )
    for template in catalog.templates:
        for source_id in template.sources:
            if source_id not in known:
                problems.append(f"template {template.id} names unknown id {source_id}")
        for ref in template.extras:
            if ref.startswith("country:"):
                if ref[len("country:") :] not in table_names:
                    problems.append(
                        f"template {template.id}: unknown country table {ref}"
                    )
            elif ref not in known:
                problems.append(f"template {template.id} names unknown id {ref}")
    for entry in catalog.deck.base:
        if entry.id not in known and entry.id != "weather":
            problems.append(f"deck entry names unknown id {entry.id}")
        if entry.swap is not None and entry.swap not in table_names:
            problems.append(
                f"deck entry {entry.id}: unknown country table {entry.swap}"
            )
        for ref in entry.inject_after:
            if ref.startswith("country:"):
                if ref[len("country:") :] not in table_names:
                    problems.append(
                        f"deck entry {entry.id}: unknown country table {ref}"
                    )
            elif ref not in known:
                problems.append(f"deck entry {entry.id} injects unknown id {ref}")
    template_ids = {template.id for template in catalog.templates}
    for country, profile in catalog.deck.briefing_profile_by_country.items():
        if profile not in template_ids:
            problems.append(
                f"briefing profile {profile} for {country} is not a Starter"
            )
    if problems:
        raise CatalogError(
            "; ".join(problems[:20]) + (" ..." if len(problems) > 20 else "")
        )
