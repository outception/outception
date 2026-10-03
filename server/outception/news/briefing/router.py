"""Which profiles a cluster is scored for: by its publishers first (the
Starter's roster plus the profile's extras), and through one route
question only for a story no profile's sources carry but several
publishers do."""

from collections.abc import Iterable

from .profiles import Profile

ROUTE_MIN_PUBLISHERS = 3


def by_sources(source_ids: Iterable[str], profiles: dict[str, Profile]) -> list[str]:
    sources = set(source_ids)
    return [pid for pid, profile in profiles.items() if sources & profile.sources]


def needs_route_question(
    source_ids: Iterable[str], publisher_count: int, profiles: dict[str, Profile]
) -> bool:
    return (
        not by_sources(source_ids, profiles) and publisher_count >= ROUTE_MIN_PUBLISHERS
    )
