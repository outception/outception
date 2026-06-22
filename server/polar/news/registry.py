"""Registry mapping source ids to their async getters.

Scraper modules call ``register()`` at import time (the ``sources``
package imports every module), mirroring the upstream glob-import
mechanism. A request can only ever reach a registered getter — there is
no path from user input to an arbitrary URL.
"""

from collections.abc import Awaitable, Callable

from .metadata import SOURCES
from .schemas import NewsItem

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
    from .cache import DEFAULT_INTERVAL_MS

    return SOURCES.get(source_id, {}).get("interval", DEFAULT_INTERVAL_MS)
