"""The registry view of the catalog: what the sources route serves, what a
request may resolve, and the search subset. Order is load-bearing: it fixes
the ETag bytes, the search result order and the always-warm head.

The key gate lives here, not in the loader: tables whose provider needs a
key are dropped from the roster when the key is unset, so no card can ever
render broken, and the loader stays pure data.
"""

import hashlib
import json
from dataclasses import dataclass
from functools import cached_property

from outception.config import settings
from outception.news.schemas import SourceMeta

from .loader import Catalog
from .schemas import COLUMN_ORDER, SourceRow

DEFAULT_INTERVAL_MS = 2 * 60 * 1000

# Table providers that only serve with a registration key.
KEYED_PROVIDERS: dict[str, str] = {
    "finnhub": "FINNHUB_API_KEY",
    "cricket": "CRICKETDATA_API_KEY",
}

META_FIELDS = (
    "name",
    "color",
    "column",
    "type",
    "home",
    "title",
    "desc",
    "redirect",
    "logo",
)
SEARCH_FIELDS = ("name", "color", "column", "type", "home")


def _gated_out(row: SourceRow) -> bool:
    if row.type != "heatmap":
        return False
    provider = str(row.config.get("provider", ""))
    field = KEYED_PROVIDERS.get(provider)
    return field is not None and not getattr(settings, field)


def _meta(row: SourceRow, fields: tuple[str, ...]) -> SourceMeta:
    payload: dict[str, object] = {
        "id": row.id,
        "interval": row.interval or DEFAULT_INTERVAL_MS,
    }
    for key in fields:
        value = getattr(row, key)
        if value is not None:
            payload[key] = value
    return SourceMeta.model_validate(payload)


@dataclass(frozen=True)
class Registry:
    catalog: Catalog

    @cached_property
    def rows(self) -> dict[str, SourceRow]:
        """Every row the roster knows, in registration order, minus the
        key-gated tables and the live signals not yet switched on."""
        dark = {signal.id for signal in self.catalog.live_signals if not signal.enabled}
        return {
            row.id: row
            for row in self.catalog.sources
            if not _gated_out(row) and row.id not in dark
        }

    @cached_property
    def ordered(self) -> list[SourceRow]:
        """Registration order, stable-sorted by column rank, disabled rows
        excluded: the order the sources route serves and the warmer reads."""
        return sorted(
            (row for row in self.rows.values() if row.id not in self.catalog.disabled),
            key=lambda row: COLUMN_ORDER.get(row.column or "", len(COLUMN_ORDER)),
        )

    @cached_property
    def payload(self) -> list[SourceMeta]:
        return [_meta(row, META_FIELDS) for row in self.ordered]

    @cached_property
    def by_id(self) -> dict[str, SourceMeta]:
        return {meta.id: meta for meta in self.payload}

    @cached_property
    def body(self) -> bytes:
        """The pre-serialized `/sources` body. Serialized once per process so
        a request never re-validates ten thousand models."""
        return json.dumps(
            [m.model_dump(by_alias=True, exclude_none=True) for m in self.payload],
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode()

    @cached_property
    def etag(self) -> str:
        return f'"{hashlib.md5(self.body).hexdigest()[:20]}"'

    @cached_property
    def search_index(self) -> list[tuple[str, str, SourceMeta]]:
        """(lowercased id, lowercased name, five-field subset) in registration
        order, aliases and disabled rows left out: what source search scans."""
        return [
            (row.id.lower(), (row.name or "").lower(), _meta(row, SEARCH_FIELDS))
            for row in self.rows.values()
            if not row.redirect and row.id not in self.catalog.disabled
        ]

    def is_known(self, source_id: str) -> bool:
        return source_id in self.rows

    def is_disabled(self, source_id: str) -> bool:
        return source_id in self.catalog.disabled

    def has_getter(self, source_id: str) -> bool:
        row = self.rows.get(source_id)
        return row is not None and row.adapter is not None

    def resolve(self, source_id: str) -> str | None:
        """Follow a redirect alias to the canonical id. None when the id is
        unknown or has no adapter (tables and strips are served elsewhere)."""
        row = self.rows.get(source_id)
        if row is None:
            return None
        if row.redirect:
            source_id = row.redirect
        if not self.has_getter(source_id):
            return None
        return source_id

    def resolve_known(self, source_id: str) -> str | None:
        """Follow a redirect alias to the canonical catalogue id, adapter or
        not: tables have no adapter but are followable like any card. None
        when the id is unknown or disabled."""
        row = self.rows.get(source_id)
        if row is None:
            return None
        source_id = row.redirect or source_id
        if source_id not in self.rows or source_id in self.catalog.disabled:
            return None
        return source_id

    def interval_ms(self, source_id: str) -> int:
        row = self.rows.get(source_id)
        if row is None or row.interval is None:
            return DEFAULT_INTERVAL_MS
        return row.interval
