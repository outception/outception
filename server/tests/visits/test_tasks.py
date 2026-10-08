from unittest.mock import AsyncMock

import pytest
from pytest_mock import MockerFixture

from outception.integrations.counter.exceptions import CounterError
from outception.visits import tasks


@pytest.mark.asyncio
class TestSync:
    async def test_skips_when_unconfigured(self, mocker: MockerFixture) -> None:
        mocker.patch("outception.visits.tasks.counter.configured", return_value=False)
        fetch = mocker.patch(
            "outception.visits.tasks.counter.fetch_visits", AsyncMock()
        )
        await tasks.sync()
        fetch.assert_not_called()

    async def test_stores_each_dimension_even_when_one_fails(
        self, mocker: MockerFixture
    ) -> None:
        mocker.patch("outception.visits.tasks.counter.configured", return_value=True)
        mocker.patch(
            "outception.visits.tasks.counter.fetch_visits",
            AsyncMock(side_effect=[["path-row"], CounterError("down")]),
        )
        upsert = mocker.patch(
            "outception.visits.tasks.service.upsert", AsyncMock(return_value=1)
        )
        await tasks.sync()
        upsert.assert_awaited_once()
        assert upsert.call_args.args[1] == ["path-row"]

    async def test_a_storage_failure_on_one_dimension_spares_the_other(
        self, mocker: MockerFixture
    ) -> None:
        from sqlalchemy.exc import IntegrityError

        mocker.patch("outception.visits.tasks.counter.configured", return_value=True)
        mocker.patch(
            "outception.visits.tasks.counter.fetch_visits",
            AsyncMock(side_effect=[["path-row"], ["country-row"]]),
        )
        upsert = mocker.patch(
            "outception.visits.tasks.service.upsert",
            AsyncMock(side_effect=[IntegrityError("insert", {}, Exception()), 1]),
        )
        await tasks.sync()
        assert [call.args[1] for call in upsert.call_args_list] == [
            ["path-row"],
            ["country-row"],
        ]
