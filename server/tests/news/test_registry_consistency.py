"""Guards against a catalog row that nothing serves, and a getter that nothing
declares: a second register() for an id replaces the first getter without any
warning, so a data row re-listing an existing feed would quietly hijack it."""

from collections import Counter

import outception.news.sources  # noqa: F401 - registers every getter
from outception.news.catalog import registry as catalog_registry
from outception.news.registry import DISABLED_SOURCES, GETTERS, SOURCES, resolve

_KNOWN_SHARED_CHANNELS = {
    "UCsooa4yRKGN_zEE8iknghZA",
    "UCZYTClx2T1of7BRZ86-8fow",
    "UCUHW94eEFW7hkUMVaZz4eDg",
    "UCRijo3ddMTht_IHyNSNXpNQ",
}


class TestRegistryConsistency:
    def test_youtube_channels_unique(self) -> None:
        channels = [
            str(row.config["channel_id"])
            for row in catalog_registry().rows.values()
            if row.adapter == "youtube"
        ]
        dupes = {c for c, n in Counter(channels).items() if n > 1}
        # Four pairs came over from the live tree sharing one channel (TED and
        # TED-Ed, SciShow and SciShow Space, minutephysics and MinuteEarth,
        # Dude Perfect and its second channel). They are on the catalog audit
        # list; the guard holds the line at four until that audit lands.
        assert dupes <= _KNOWN_SHARED_CHANNELS, (
            f"new duplicate channels in the catalog: {dupes - _KNOWN_SHARED_CHANNELS}"
        )

    def test_every_catalog_row_has_a_getter(self) -> None:
        missing = [
            sid
            for sid in SOURCES
            if sid not in DISABLED_SOURCES
            # Table cards have no headline getter by design: their tiles are
            # served by /news/heatmap/{id} (see news/heatmap.py).
            and SOURCES[sid].get("type") not in ("heatmap", "game")
            and resolve(sid) not in GETTERS
        ]
        assert not missing, missing[:10]

    def test_every_getter_has_a_catalog_row(self) -> None:
        orphans = [sid for sid in GETTERS if sid not in SOURCES]
        assert not orphans, orphans[:10]
