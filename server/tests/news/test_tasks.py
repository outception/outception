import json

import pytest
from pytest_mock import MockerFixture

from outception.news import cache, heatmap, tasks
from outception.news.cache import now_ms
from outception.news.endpoints import SOURCE_DEMAND_KEY
from outception.news.schemas import NewsItem
from outception.news.tasks import warm_demanded_sources
from outception.redis import Redis

_WORLD_SPEC = heatmap.HEATMAPS["heatmap-world-buzz"]


def _demand(heatmap_id: str = "heatmap-world-buzz") -> str:
    return heatmap._DEMAND_KEY.format(id=heatmap_id)


def _family_ids(count: int) -> list[str]:
    return sorted(source_id for source_id, _, _ in heatmap.buzz_family(_WORLD_SPEC))[
        :count
    ]


def _item() -> NewsItem:
    return NewsItem(
        id="story", title="headline", url="https://example.com", pub_date=now_ms()
    )


@pytest.fixture(autouse=True)
def _worker_redis(redis: Redis, mocker: MockerFixture) -> None:
    mocker.patch("outception.news.tasks.create_redis", return_value=redis)
    mocker.patch.object(redis, "close", new=mocker.AsyncMock())
    mocker.patch("outception.news.tasks.asyncio.sleep", new=mocker.AsyncMock())


def test_tasks_module_registers_getters() -> None:
    """The worker imports tasks.py without ever touching api.py — the module
    itself must trigger source registration or the warmer warms nothing."""
    import outception.news.tasks  # noqa: F401
    from outception.news.registry import GETTERS

    assert GETTERS


@pytest.mark.asyncio
class TestWarmDemandedSources:
    async def test_no_demand_no_fetches(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        getter = mocker.AsyncMock(return_value=[_item()])
        mocker.patch.dict(
            "outception.news.registry.GETTERS",
            dict.fromkeys(_family_ids(3), getter),
            clear=True,
        )

        await warm_demanded_sources()

        getter.assert_not_called()

    async def test_warms_demanded_stale_family(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        ids = _family_ids(2)
        getter = mocker.AsyncMock(return_value=[_item()])
        mocker.patch.dict(
            "outception.news.registry.GETTERS",
            dict.fromkeys(ids, getter),
            clear=True,
        )
        await redis.set(_demand(), "1")

        await warm_demanded_sources()

        assert getter.await_count == 2
        for source_id in ids:
            entry = await cache.get(redis, source_id)
            assert entry is not None
            assert entry.items[0].title == "headline"

    async def test_fresh_entries_are_skipped(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        fresh_id, stale_id = _family_ids(2)
        getter = mocker.AsyncMock(return_value=[_item()])
        mocker.patch.dict(
            "outception.news.registry.GETTERS",
            {fresh_id: getter, stale_id: getter},
            clear=True,
        )
        await redis.set(_demand(), "1")
        await redis.set(
            cache.cache_key(fresh_id), json.dumps({"updated": now_ms(), "items": []})
        )

        await warm_demanded_sources()

        assert getter.await_count == 1
        assert (await cache.get(redis, stale_id)) is not None

    async def test_fetch_cap_and_cursor_rotation(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        first, second = _family_ids(2)
        calls: list[str] = []

        def make_getter(source_id: str):  # type: ignore[no-untyped-def]
            async def getter() -> list[NewsItem]:
                calls.append(source_id)
                return [_item()]

            return getter

        mocker.patch.dict(
            "outception.news.registry.GETTERS",
            {first: make_getter(first), second: make_getter(second)},
            clear=True,
        )
        mocker.patch("outception.news.tasks._BUZZ_FETCH_CAP", 1)
        await redis.set(_demand(), "1")

        await warm_demanded_sources()
        assert calls == [first]

        await warm_demanded_sources()
        assert calls == [first, second]

    async def test_warms_individually_viewed_source(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        getter = mocker.AsyncMock(return_value=[_item()])
        mocker.patch.dict(
            "outception.news.registry.GETTERS",
            {"dailymail": getter},
            clear=True,
        )
        await redis.set(SOURCE_DEMAND_KEY.format(id="dailymail"), "1")

        await warm_demanded_sources()

        assert getter.await_count == 1
        assert (await cache.get(redis, "dailymail")) is not None

    async def test_circuit_breaker_backs_off(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        ids = _family_ids(4)
        getter = mocker.AsyncMock(side_effect=RuntimeError("blocked"))
        mocker.patch.dict(
            "outception.news.registry.GETTERS",
            dict.fromkeys(ids, getter),
            clear=True,
        )
        mocker.patch("outception.news.tasks._BUZZ_FAILURE_TRIP", 2)
        await redis.set(_demand(), "1")

        await warm_demanded_sources()

        assert getter.await_count == 2
        assert await redis.get(tasks._BUZZ_BACKOFF_KEY)

        await warm_demanded_sources()
        assert getter.await_count == 2
