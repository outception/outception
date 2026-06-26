"""Scraper modules. Importing this package registers every source
getter (each module calls ``registry.register`` / ``@source`` at import
time). Keep imports alphabetical; one module per upstream source file.
"""

from . import (
    arstechnica,  # noqa: F401
    bbc,  # noqa: F401
    bluesky,  # noqa: F401
    faa,  # noqa: F401
    feeds,  # noqa: F401
    github,  # noqa: F401
    gnews,  # noqa: F401
    guardian,  # noqa: F401
    hackernews,  # noqa: F401
    lobsters,  # noqa: F401
    mastodon,  # noqa: F401
    npr,  # noqa: F401
    nytimes,  # noqa: F401
    producthunt,  # noqa: F401
    reddit,  # noqa: F401
    steam,  # noqa: F401
    techcrunch,  # noqa: F401
    theverge,  # noqa: F401
    weather,  # noqa: F401
    wired,  # noqa: F401
    youtube,  # noqa: F401
)
