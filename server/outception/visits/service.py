from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from outception.integrations.counter.schemas import Dimension, VisitRow
from outception.kit.utils import utc_now
from outception.models import SiteVisit
from outception.postgres import AsyncSession

from .schemas import Race
from .series import zero_fill

WINDOW_DAYS = 30
# Bars worth racing: the keys with the most views over the window.
TOP_KEYS = 12


async def upsert(session: AsyncSession, rows: Sequence[VisitRow]) -> int:
    """Store the counter's daily totals, replacing any earlier value for the
    same day and key (the counter reports absolute counts)."""
    if not rows:
        return 0
    statement = pg_insert(SiteVisit).values(
        [
            {
                "day": row.day,
                "dimension": row.dimension,
                "key": row.key,
                "views": row.views,
            }
            for row in rows
        ]
    )
    await session.execute(
        statement.on_conflict_do_update(
            index_elements=["dimension", "day", "key"],
            set_={"views": statement.excluded.views, "modified_at": utc_now()},
        )
    )
    return len(rows)


async def race(
    session: AsyncSession, dimension: Dimension, days: int = WINDOW_DAYS
) -> Race:
    today = datetime.now(UTC).date()
    since = today - timedelta(days=days)
    result = await session.execute(
        select(SiteVisit.day, SiteVisit.key, SiteVisit.views).where(
            SiteVisit.dimension == dimension, SiteVisit.day >= since
        )
    )
    points: dict[tuple[date, str], int] = {}
    totals: dict[str, int] = {}
    for day, key, views in result.all():
        points[(day, key)] = int(views)
        totals[key] = totals.get(key, 0) + int(views)
    names = sorted(totals, key=lambda key: (-totals[key], key))[:TOP_KEYS]
    kept = {point: value for point, value in points.items() if point[1] in names}
    return Race(mode="visits", rows=zero_fill(kept, names, since, today))
