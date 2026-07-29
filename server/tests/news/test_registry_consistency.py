"""Guards against silently double-registered sources: a second register()
for an id replaces the first getter without any warning, so a data file
re-listing an existing feed quietly hijacks it (and the metadata row keeps
the old category — the mismatch that shipped five miscategorized sources)."""

from collections import Counter

import outception.news.sources  # noqa: F401 — registers every getter
from outception.news.metadata import SOURCES
from outception.news.registry import GETTERS
from outception.news.shopping_data import SHOPPING_FEEDS
from outception.news.youtube_extra import YOUTUBE_EXTRA


class TestRegistryConsistency:
    def test_shopping_feed_ids_do_not_shadow_other_sources(self) -> None:
        for sid, _url, _name, column, _home in SHOPPING_FEEDS:
            assert SOURCES[sid]["column"] == column, (
                f"{sid}: shopping row says {column!r} but metadata kept "
                f"{SOURCES[sid]['column']!r} — duplicate registration"
            )

    def test_youtube_channels_unique(self) -> None:
        chan_rows = [cid for cid, _sid, _n, _c in YOUTUBE_EXTRA]
        dupes = [c for c, n in Counter(chan_rows).items() if n > 1]
        assert not dupes, f"duplicate channels in YOUTUBE_EXTRA: {dupes}"

    def test_every_metadata_row_has_a_getter(self) -> None:
        from outception.news.registry import DISABLED_SOURCES, resolve

        missing = [
            sid
            for sid in SOURCES
            if sid not in DISABLED_SOURCES and resolve(sid) not in GETTERS
        ]
        assert not missing, missing[:10]
