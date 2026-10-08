"""Views per day by page path and by visitor country, from the counter."""

from datetime import date

from . import client
from .schemas import Dimension, VisitRow

_FIELDS: dict[Dimension, str] = {
    "path": "properties.$pathname",
    "country": "properties.$geoip_country_code",
}

# Bars worth keeping per dimension over the window; the chart shows fewer.
TOP_KEYS = 24
# One day more than the chart's window, so the day that drops out of the
# window was complete when it was last stored.
WINDOW_DAYS = 31


def hogql(dimension: Dimension, days: int = WINDOW_DAYS) -> str:
    """Daily views for the top keys of the window. Days are UTC days, like
    everything the server stores, whatever the project's own timezone; the
    window opens at midnight so the oldest day is never a partial count.
    The top keys come from a subquery, so no value from the data is ever
    written into the query text."""
    field = _FIELDS[dimension]
    since = f"toStartOfDay(toTimeZone(now(), 'UTC')) - interval {int(days)} day"
    pageviews = f"event = '$pageview' and timestamp >= {since} and {field} is not null"
    return (
        f"select toDate(toTimeZone(timestamp, 'UTC')) as day, {field} as key, "
        "count() as views from events "
        f"where {pageviews} and {field} in ("
        f"select {field} from events where {pageviews} "
        f"group by {field} order by count() desc limit {TOP_KEYS}"
        ") group by day, key order by day desc, views desc limit 5000"
    )


def parse(dimension: Dimension, rows: list[list[object]]) -> list[VisitRow]:
    """The counter's rows as visit rows. Keys are cut to what the table
    holds, and two keys that become one after the cut are summed into one
    row: a single insert must never carry the same (day, key) twice, which
    the database refuses for the whole batch."""
    views_by: dict[tuple[date, str], int] = {}
    for row in rows:
        if len(row) < 3 or row[1] in (None, ""):
            continue
        day_text = str(row[0])[:10]
        try:
            day = date.fromisoformat(day_text)
            views = int(row[2])  # type: ignore[call-overload]
        except TypeError, ValueError:
            continue
        key = (day, str(row[1])[:200])
        views_by[key] = views_by.get(key, 0) + views
    return [
        VisitRow(day=day, dimension=dimension, key=key, views=views)
        for (day, key), views in views_by.items()
    ]


async def fetch_visits(dimension: Dimension, days: int = WINDOW_DAYS) -> list[VisitRow]:
    """One dimension's daily rows for the window."""
    results = await client.query(hogql(dimension, days), name=f"visits by {dimension}")
    return parse(dimension, results)


DIMENSIONS: tuple[Dimension, ...] = ("path", "country")

configured = client.configured
