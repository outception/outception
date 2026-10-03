"""The runtime registry: source ids to their async getters, over the
catalog. Adapters call `register` at import time (the `sources` package
imports every module and builds the data-driven getters), so a request can
only ever reach a registered getter; there is no path from user input to an
arbitrary URL.

`SOURCES` and `DISABLED_SOURCES` are the catalog's rows and audit list in
the shapes the ported modules read; the catalog registry owns the order,
the key gate and the serialized body.
"""

from collections.abc import Awaitable, Callable

from .catalog import registry as catalog_registry
from .catalog.registry import DEFAULT_INTERVAL_MS
from .schemas import NewsItem

Getter = Callable[[], Awaitable[list[NewsItem]]]

GETTERS: dict[str, Getter] = {}

_registry = catalog_registry()

# id -> the row's meta fields, in registration order, key-gated tables left
# out: what the live metadata module used to hold.
SOURCES: dict[str, dict[str, object]] = {
    row.id: {
        key: value
        for key, value in (
            ("name", row.name),
            ("color", row.color),
            ("column", row.column),
            ("type", row.type),
            ("home", row.home),
            ("title", row.title),
            ("desc", row.desc),
            ("interval", row.interval),
            ("redirect", row.redirect),
            ("logo", row.logo),
        )
        if value is not None
    }
    for row in _registry.rows.values()
}

DISABLED_SOURCES: frozenset[str] = frozenset(_registry.catalog.disabled)


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
        source_id = str(redirect)
    if source_id not in SOURCES or source_id not in GETTERS:
        return None
    return source_id


def resolve_known(source_id: str) -> str | None:
    """Follow a redirect alias to the canonical catalog id, getter or not:
    table cards have no getter (their tiles come from their own endpoint)
    but are followable like any card. None when the id is unknown or
    disabled."""
    meta = SOURCES.get(source_id)
    if meta is None:
        return None
    redirect = meta.get("redirect")
    if redirect:
        source_id = str(redirect)
    if source_id not in SOURCES or source_id in DISABLED_SOURCES:
        return None
    return source_id


def interval_ms(source_id: str) -> int:
    meta = SOURCES.get(source_id)
    if meta is None:
        return DEFAULT_INTERVAL_MS
    interval = meta.get("interval")
    return interval if isinstance(interval, int) else DEFAULT_INTERVAL_MS
