"""Getters built from the catalog rows: every row with a data-driven
adapter family gets one, registered under its id. The special cases
(scrapers over HTML and JSON APIs) register themselves in their modules;
the video channels do in `youtube`."""

from ..catalog import registry as catalog_registry
from ..registry import register
from . import rss

FAMILIES = {
    "rss": lambda sid, cfg: rss.rss(sid, str(cfg["url"])),
    "rss_lenient": lambda sid, cfg: rss.rss_lenient(sid, str(cfg["url"])),
    "gnews": lambda sid, cfg: rss.gnews(sid, str(cfg["url"])),
    "search": lambda sid, cfg: rss.search(sid, str(cfg["url"])),
    "shopping": lambda sid, cfg: rss.shopping(
        sid,
        str(cfg["url"]),
        int(cfg.get("max_age_days", 60)),
    ),
}

for _row in catalog_registry().rows.values():
    _build = FAMILIES.get(_row.adapter or "")
    if _build is not None:
        register(_row.id, _build(_row.id, _row.config))
