"""Zero-filling for the race: a bar that has no row for a day would jump,
so every name gets a value for every day of the window."""

from collections.abc import Iterable, Mapping
from datetime import date, timedelta

from .schemas import RaceRow


def zero_fill(
    points: Mapping[tuple[date, str], int],
    names: Iterable[str],
    since: date,
    until: date,
) -> list[RaceRow]:
    """Every name for every day from the first day that has any value (a
    race that opens on weeks of empty bars tells nothing) up to `until`."""
    ordered = sorted(set(names))
    rows: list[RaceRow] = []
    first = min((day for (day, _), value in points.items() if value), default=None)
    if first is not None and first > since:
        since = first
    day = since
    while day <= until:
        for name in ordered:
            rows.append(RaceRow(date=day, name=name, value=points.get((day, name), 0)))
        day += timedelta(days=1)
    return rows
