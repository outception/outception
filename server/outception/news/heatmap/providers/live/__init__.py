"""The live signals: keyless upstreams polled by the worker, served as
table cards. Each module exposes `fetch_tiles(redis, spec)` like every
other provider, and the builders are registered by id here."""

from . import iss, launches, quakes, storms, transit, wildfires

LIVE_BUILDERS = {
    "quakes": quakes.fetch_tiles,
    "storms": storms.fetch_tiles,
    "wildfires": wildfires.fetch_tiles,
    "launches": launches.fetch_tiles,
    "iss": iss.fetch_tiles,
    "transit": transit.fetch_tiles,
}
