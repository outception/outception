"""Source adapters. Importing this package registers every getter: the
special cases register themselves, the data-driven families are built from
the catalog rows by `generated`. Keep the imports alphabetical."""

from . import (
    bluesky,  # noqa: F401
    faa,  # noqa: F401
    fun,  # noqa: F401
    generated,  # noqa: F401
    github,  # noqa: F401
    hackernews,  # noqa: F401
    lobsters,  # noqa: F401
    mastodon,  # noqa: F401
    products,  # noqa: F401
    steam,  # noqa: F401
    youtube,  # noqa: F401
)
