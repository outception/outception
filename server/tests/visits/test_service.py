from datetime import UTC, date, datetime, timedelta

import pytest

from outception.integrations.counter.schemas import VisitRow
from outception.postgres import AsyncSession
from outception.visits import service
from outception.visits.series import zero_fill


def test_zero_fill_gives_every_name_every_day() -> None:
    rows = zero_fill(
        {(date(2026, 10, 2), "a"): 3, (date(2026, 10, 1), "b"): 1},
        ["b", "a"],
        date(2026, 9, 20),
        date(2026, 10, 3),
    )
    # Opens on the first day with a value, not on the empty weeks before.
    assert [(r.date.day, r.name, r.value) for r in rows] == [
        (1, "a", 0),
        (1, "b", 1),
        (2, "a", 3),
        (2, "b", 0),
        (3, "a", 0),
        (3, "b", 0),
    ]


def test_zero_fill_without_values_keeps_the_window() -> None:
    rows = zero_fill({}, ["a"], date(2026, 10, 1), date(2026, 10, 2))
    assert [(r.date.day, r.value) for r in rows] == [(1, 0), (2, 0)]


@pytest.mark.asyncio
class TestVisits:
    async def test_upsert_replaces_and_race_fills(self, session: AsyncSession) -> None:
        today = datetime.now(UTC).date()
        yesterday = today - timedelta(days=1)
        await service.upsert(
            session,
            [
                VisitRow(day=yesterday, dimension="path", key="/", views=5),
                VisitRow(day=today, dimension="path", key="/", views=2),
                VisitRow(day=today, dimension="path", key="/launches", views=9),
                VisitRow(day=today, dimension="country", key="IE", views=7),
            ],
        )
        # A later sync carries the day's final count, not an increment.
        await service.upsert(
            session, [VisitRow(day=today, dimension="path", key="/", views=4)]
        )
        await session.flush()
        race = await service.race(session, "path", days=2)
        assert race.mode == "visits"
        by_day = {(r.date, r.name): r.value for r in race.rows}
        assert by_day[(today, "/")] == 4
        assert by_day[(yesterday, "/")] == 5
        assert by_day[(today, "/launches")] == 9
        assert by_day[(yesterday, "/launches")] == 0
        assert len(race.rows) == 2 * 2  # from the first day with data
        countries = await service.race(session, "country", days=2)
        assert {r.name for r in countries.rows} == {"IE"}

    async def test_empty_table_is_an_empty_race(self, session: AsyncSession) -> None:
        race = await service.race(session, "country", days=2)
        assert race.rows == []

    async def test_race_keeps_only_the_top_keys(self, session: AsyncSession) -> None:
        today = datetime.now(UTC).date()
        rows = [
            VisitRow(day=today, dimension="path", key=f"/p{n}", views=100 - n)
            for n in range(service.TOP_KEYS + 5)
        ]
        await service.upsert(session, rows)
        await session.flush()
        race = await service.race(session, "path", days=1)
        names = {r.name for r in race.rows}
        assert len(names) == service.TOP_KEYS
        assert "/p0" in names
        assert f"/p{service.TOP_KEYS + 4}" not in names
