import json
import time

import dramatiq
import pytest
from pytest_mock import MockerFixture

from outception.news import cache, heatmap, registry, tasks, translate
from outception.news.cache import now_ms
from outception.news.endpoints import SOURCE_DEMAND_KEY
from outception.news.registry import DISABLED_SOURCES
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


@pytest.mark.parametrize(
    ("actor_name", "budget_seconds"),
    [
        ("news.warm_translations", tasks._RUN_BUDGET_SECONDS),
        ("news.warm_demanded_sources", tasks._BUZZ_RUN_BUDGET_SECONDS),
    ],
)
def test_warmer_time_limit_exceeds_run_budget(
    actor_name: str, budget_seconds: int
) -> None:
    """A warmer's dramatiq time limit must outlast its own run budget, or the
    broker kills the run before the budget-aware loop can stop cleanly."""
    time_limit_ms = dramatiq.get_broker().get_actor(actor_name).options["time_limit"]

    assert time_limit_ms > budget_seconds * 1000


def test_tasks_module_registers_getters() -> None:
    """The worker imports tasks.py without ever touching api.py — the module
    itself must trigger source registration or the warmer warms nothing."""
    import outception.news.tasks  # noqa: F401
    from outception.news.registry import GETTERS

    assert GETTERS


@pytest.mark.asyncio
class TestWarmTranslations:
    async def test_only_demanded_languages_are_warmed(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        source_id = tasks._deck_sources()[0]
        await cache.set(redis, source_id, [_item()])
        translate_texts = mocker.patch.object(
            translate, "translate_texts", mocker.AsyncMock(return_value=["x"])
        )

        await tasks.warm_translations()
        translate_texts.assert_not_awaited()  # nobody asked for any language

        await translate.note_demand(redis, "de")
        await tasks.warm_translations()
        targets = {call.args[2] for call in translate_texts.await_args_list}
        assert targets == {"de"}
        assert all(
            call.kwargs.get("budget") == "warmer"
            for call in translate_texts.await_args_list
        )


@pytest.mark.asyncio
class TestAlwaysWarmSources:
    """The set kept warm with no demand behind it, so headline search covers
    the big outlets instead of only whatever was recently viewed. It rides the
    demanded-source rotation, and must not be able to swamp it."""

    async def test_warms_a_source_nobody_viewed(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        source_id = sorted(tasks.ALWAYS_WARM_IDS)[0]
        getter = mocker.AsyncMock(return_value=[_item()])
        mocker.patch.dict(
            "outception.news.registry.GETTERS", {source_id: getter}, clear=True
        )

        await warm_demanded_sources()

        getter.assert_awaited()
        entry = await cache.get(redis, source_id)
        assert entry is not None

    async def test_stays_inside_the_rotation_budget(self) -> None:
        """One fetch keeps a source warm for `_BUZZ_STALE_AFTER_MS`, and the
        cron gives that many runs of `_BUZZ_FETCH_CAP` in the same window. The
        always-warm set has to leave most of that for real readers — crowding
        them out would make the wall slower, not faster."""
        window_minutes = tasks._BUZZ_STALE_AFTER_MS / 1000 / 60
        runs_per_window = window_minutes / 10  # the cron fires every 10 min
        capacity = runs_per_window * tasks._BUZZ_FETCH_CAP

        assert len(tasks.ALWAYS_WARM_IDS) < capacity / 2

    async def test_only_includes_fetchable_sources(self) -> None:
        # Heatmap/game/weather cards have no feed to fetch, and a disabled
        # source must never be fetched at all.
        for source_id in tasks.ALWAYS_WARM_IDS:
            assert source_id in registry.GETTERS
            assert source_id not in DISABLED_SOURCES

    async def test_warming_a_card_pretaps_its_heroes(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        """A freshly-warmed card's top headlines join the summary warm queue
        ("pre-tapped"), so the first human tap on a story the warmer has seen
        is a cache hit — not the cold path."""
        source_id = sorted(tasks.ALWAYS_WARM_IDS)[0]
        getter = mocker.AsyncMock(return_value=[_item()])
        mocker.patch.dict(
            "outception.news.registry.GETTERS", {source_id: getter}, clear=True
        )
        mocker.patch("outception.news.summary.gemini.configured", return_value=True)

        await warm_demanded_sources()

        queued = {
            m.decode() if isinstance(m, bytes) else m
            for m in await redis.smembers("news:summary:warm")
        }
        assert "en\thttps://example.com" in queued


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
        await redis.zadd(SOURCE_DEMAND_KEY, {"dailymail": time.time()})

        await warm_demanded_sources()

        assert getter.await_count == 1
        assert (await cache.get(redis, "dailymail")) is not None

    async def test_empty_fetch_keeps_last_good_headlines(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        (source_id,) = _family_ids(1)
        getter = mocker.AsyncMock(return_value=[])
        mocker.patch.dict(
            "outception.news.registry.GETTERS", {source_id: getter}, clear=True
        )
        await redis.set(_demand(), "1")
        stale = now_ms() - tasks._BUZZ_STALE_AFTER_MS - 1
        await redis.set(
            cache.cache_key(source_id),
            json.dumps({"updated": stale, "items": [_item().model_dump()]}),
        )

        await warm_demanded_sources()

        entry = await cache.get(redis, source_id)
        assert entry is not None
        assert entry.updated > stale
        assert [item.title for item in entry.items] == ["headline"]

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
