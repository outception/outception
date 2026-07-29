import asyncio
import json

import pytest
from httpx import AsyncClient
from pytest_mock import MockerFixture

from outception.config import settings
from outception.exceptions import OutceptionError
from outception.news import heatmap
from outception.news.cache import now_ms
from outception.news.fetch import NewsFetchError
from outception.redis import Redis

_COINGECKO_COINS = [
    {
        "symbol": "btc",
        "name": "Bitcoin",
        "current_price": 100000.0,
        "market_cap": 2_000_000_000_000,
        "price_change_percentage_24h": 1.234,
    },
    {
        "symbol": "eth",
        "name": "Ethereum",
        "current_price": 4000.0,
        "market_cap": 500_000_000_000,
        "price_change_percentage_24h": -2.5,
    },
    # No market cap → dropped rather than sized arbitrarily.
    {
        "symbol": "junk",
        "name": "Junk",
        "current_price": 1.0,
        "market_cap": None,
        "price_change_percentage_24h": 0.5,
    },
]


@pytest.mark.asyncio
class TestGetHeatmapEndpoint:
    async def test_unknown_heatmap_returns_404(self, client: AsyncClient) -> None:
        response = await client.get("/v1/news/heatmap/heatmap-nope")
        assert response.status_code == 404

    async def test_crypto_success(
        self, client: AsyncClient, mocker: MockerFixture
    ) -> None:
        mocker.patch(
            "outception.news.heatmap.fetch_json", return_value=_COINGECKO_COINS
        )
        response = await client.get("/v1/news/heatmap/heatmap-crypto")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "success"
        assert payload["id"] == "heatmap-crypto"
        symbols = [tile["symbol"] for tile in payload["tiles"]]
        assert symbols == ["BTC", "ETH"]  # capless coin dropped
        assert payload["tiles"][0]["changePercent"] == 1.23
        assert payload["tiles"][0]["weight"] == 2_000_000_000_000

    async def test_cold_cache_upstream_failure_is_502(
        self, client: AsyncClient, mocker: MockerFixture
    ) -> None:
        mocker.patch(
            "outception.news.heatmap.fetch_json",
            side_effect=NewsFetchError("down"),
        )
        response = await client.get("/v1/news/heatmap/heatmap-crypto")
        assert response.status_code == 502


@pytest.mark.asyncio
class TestGetHeatmapCache:
    async def test_fresh_cache_skips_upstream(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        fetch = mocker.patch("outception.news.heatmap.fetch_json")
        cached = {
            "id": "heatmap-crypto",
            "updatedTime": now_ms(),
            "tiles": [],
        }
        await redis.set("news:heatmap:heatmap-crypto", json.dumps(cached))

        result = await heatmap.get_heatmap(redis, "heatmap-crypto")

        assert result["status"] == "success"
        fetch.assert_not_called()

    async def test_stale_cache_served_when_upstream_fails(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch(
            "outception.news.heatmap.fetch_json",
            side_effect=NewsFetchError("down"),
        )
        stale = {
            "id": "heatmap-crypto",
            "updatedTime": now_ms() - heatmap.HEATMAP_INTERVAL_MS - 1,
            "tiles": [
                {
                    "symbol": "BTC",
                    "name": "Bitcoin",
                    "changePercent": 1.0,
                    "price": 100000.0,
                    "weight": 1.0,
                }
            ],
        }
        await redis.set("news:heatmap:heatmap-crypto", json.dumps(stale))

        result = await heatmap.get_heatmap(redis, "heatmap-crypto")

        assert result["status"] == "cache"
        assert result["tiles"][0]["symbol"] == "BTC"


@pytest.mark.asyncio
class TestSingleFlight:
    async def test_concurrent_stale_requests_fetch_once(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        # A stale entry + a crowd: only the lock winner refetches; the rest
        # serve the stale payload, so upstream is hit once, not once-per-caller.
        stale = {
            "id": "heatmap-crypto",
            "updatedTime": now_ms() - heatmap.HEATMAP_INTERVAL_MS - 1,
            "tiles": [
                {
                    "symbol": "BTC",
                    "name": "Bitcoin",
                    "changePercent": 1.0,
                    "price": 1.0,
                    "weight": 1.0,
                }
            ],
        }
        await redis.set("news:heatmap:heatmap-crypto", json.dumps(stale))
        fetch = mocker.patch(
            "outception.news.heatmap.fetch_json", return_value=_COINGECKO_COINS
        )

        results = await asyncio.gather(
            *(heatmap.get_heatmap(redis, "heatmap-crypto") for _ in range(8))
        )

        # The lock guarantees the upstream is hit exactly once no matter how
        # many callers land in the stale window; losers serve cache (or the
        # winner's just-written fresh entry), never a second fetch.
        assert fetch.call_count == 1
        assert all(r["status"] in ("success", "cache") for r in results)

    async def test_partial_finnhub_not_cached_as_success(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "FINNHUB_API_KEY", "test-key")
        # A universe of 4, but only 1 quote survives (rest 429) → below the
        # half-fill floor → NewsFetchError → 502 (no stale to fall back to),
        # never a 1-tile "success" map.
        spec = heatmap.HeatmapSpec(
            name="Test",
            desc="",
            color="teal",
            provider="finnhub",
            symbols=(("A", "A"), ("B", "B"), ("C", "C"), ("D", "D")),
        )
        mocker.patch.dict(heatmap.HEATMAPS, {"heatmap-test": spec})

        async def fake_fetch(url: str, params: dict[str, object]) -> object:
            if params["symbol"] == "A" and "quote" in url:
                return {"c": 100.0, "dp": 1.0}
            if params["symbol"] == "A":
                return {"marketCapitalization": 1_000.0}
            raise NewsFetchError("429")

        mocker.patch("outception.news.heatmap.fetch_json", side_effect=fake_fetch)

        with pytest.raises(OutceptionError):
            await heatmap.get_heatmap(redis, "heatmap-test")


@pytest.mark.asyncio
class TestFrankfurterHeatmap:
    async def test_currency_change_inverts_per_dollar_rates(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        async def fake_fetch(url: str, **_: object) -> object:
            if "/latest" in url:
                # EUR strengthened: fewer EUR per USD than yesterday.
                return {"date": "2026-08-13", "rates": {"EUR": 0.90, "JPY": 150.0}}
            return {"rates": {"EUR": 0.909, "JPY": 148.5}}

        mocker.patch("outception.news.heatmap.fetch_json", side_effect=fake_fetch)

        result = await heatmap.get_heatmap(redis, "heatmap-fx")

        by_symbol = {tile["symbol"]: tile for tile in result["tiles"]}
        assert by_symbol["EUR"]["changePercent"] == 1.0  # 0.909/0.90 - 1
        assert by_symbol["JPY"]["changePercent"] == -1.0  # weakened
        assert by_symbol["EUR"]["weight"] > by_symbol["JPY"]["weight"]


def _espn_soccer_entry(
    name: str, tla: str, points: int, played: int
) -> dict[str, object]:
    wins, losses = played, 0
    return {
        "team": {"displayName": name, "abbreviation": tla},
        "stats": [
            {"name": "points", "value": points},
            {"name": "gamesPlayed", "value": played},
            {"name": "wins", "value": wins},
            {"name": "losses", "value": losses},
            {"name": "rankChange", "value": 0},
        ],
    }


@pytest.mark.asyncio
class TestSoccerHeatmap:
    async def test_served_without_any_api_key(
        self, client: AsyncClient, mocker: MockerFixture
    ) -> None:
        # Soccer tables ride ESPN's keyless standings JSON — no key gating.
        mocker.patch.object(settings, "FOOTBALL_DATA_API_KEY", None)
        mocker.patch(
            "outception.news.heatmap.fetch_json",
            return_value={
                "standings": {"entries": [_espn_soccer_entry("Arsenal", "ARS", 45, 19)]}
            },
        )
        response = await client.get("/v1/news/heatmap/heatmap-premier-league")
        assert response.status_code == 200
        assert response.json()["tiles"]

    async def test_standings_become_zone_tiles(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        # A full 20-team table: zone seats derive from the points order, so a
        # 2-team fixture would land both tiles in the "top 4" green band.
        entries = [
            _espn_soccer_entry("Arsenal", "ARS", 45, 19),
            *(
                _espn_soccer_entry(f"Club {pos}", f"C{pos}", 40 - pos, 19)
                for pos in range(2, 20)
            ),
            _espn_soccer_entry("Luton Town", "LUT", 8, 19),
        ]
        mocker.patch(
            "outception.news.heatmap.fetch_json",
            return_value={"children": [{"standings": {"entries": entries}}]},
        )

        result = await heatmap.get_heatmap(redis, "heatmap-premier-league")

        tiles = result["tiles"]
        top, bottom = tiles[0], tiles[-1]
        assert top["symbol"] == "ARS"
        assert top["label"] == "45 pts"
        # Zone coloring: 1st sits in the Champions League places (full
        # green), 20th in the relegation zone (full red).
        assert top["changePercent"] == 3.0
        assert bottom["symbol"] == "LUT"
        assert bottom["changePercent"] == -3.0
        # Sports grids are uniform: every team tile the same size.
        assert top["weight"] == 1.0
        assert bottom["weight"] == 1.0

    async def test_reset_table_backfills_last_season_final(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        reset = {
            "season": {"displayName": "2099-00 English Premier League", "year": 2099},
            "standings": {
                "entries": [
                    _espn_soccer_entry(f"Club {pos}", f"C{pos}", 0, 0)
                    for pos in range(1, 21)
                ]
            },
        }
        final = {
            "season": {"displayName": "2098-99 English Premier League", "year": 2098},
            "standings": {
                "entries": [
                    _espn_soccer_entry(f"Club {pos}", f"C{pos}", 100 - pos, 38)
                    for pos in range(1, 21)
                ]
            },
        }
        fetch = mocker.patch(
            "outception.news.heatmap.fetch_json", side_effect=[reset, final]
        )

        result = await heatmap.get_heatmap(redis, "heatmap-premier-league")

        # The archive request pins last season explicitly.
        assert fetch.call_args_list[1].kwargs["params"] == {"season": 2098}
        tiles = result["tiles"]
        # A pre-season reset serves LAST season's final table, stamped as such,
        # with qualification zones intact (champions green, drop zone red).
        assert tiles[0]["label"] == "99 pts · 98/99 final"
        assert tiles[0]["changePercent"] == 3.0
        assert tiles[-1]["changePercent"] == -3.0

    async def test_reset_table_without_archive_is_labelled_new_season(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        reset = {
            "season": {"displayName": "2099-00 English Premier League", "year": 2099},
            "standings": {
                "entries": [
                    _espn_soccer_entry(f"Club {pos}", f"C{pos}", 0, 0)
                    for pos in (1, 2, 3)
                ]
            },
        }
        # Archive fetch returns another empty table — nothing to backfill from.
        mocker.patch("outception.news.heatmap.fetch_json", side_effect=[reset, reset])

        result = await heatmap.get_heatmap(redis, "heatmap-premier-league")

        # An all-zero table for a not-yet-started season is the NEW season's
        # empty table — never "last season final", and never zone-colored.
        assert all(t["label"] == "0 pts · 99/00 season" for t in result["tiles"])
        assert all(t["changePercent"] == 0.0 for t in result["tiles"])


@pytest.mark.asyncio
class TestBuzzHeatmap:
    async def test_cached_stories_become_freshness_tiles(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        fetch = mocker.patch("outception.news.heatmap.fetch_json")
        now = now_ms()

        def entry(*ages_ms: int) -> str:
            return json.dumps(
                {
                    "updated": now,
                    "items": [
                        {
                            "id": f"i{age}",
                            "title": "headline",
                            "url": "https://example.com",
                            "pubDate": now - age,
                        }
                        for age in ages_ms
                    ],
                }
            )

        hour = 3_600_000
        # Three fresh stories, newest 1h old → big hot tile.
        await redis.set("news:source:gnews-ie", entry(hour, 5 * hour, 30 * hour))
        # One day-old story → smaller, cooler tile.
        await redis.set("news:source:gnews-us", entry(30 * hour))
        # Old-but-within-a-week news → faint tile, not absent.
        await redis.set("news:source:gnews-gb", entry(90 * hour))
        # Ancient news (>7d) → dropped entirely.
        await redis.set("news:source:gnews-au", entry(200 * hour))

        result = await heatmap.get_heatmap(redis, "heatmap-world-buzz")

        fetch.assert_not_called()  # buzz maps never call out
        by_name = {tile["name"]: tile for tile in result["tiles"]}
        # Country labels from `title` — the shared "Top Stories" feed name
        # would render every tile identically.
        assert set(by_name) == {"Ireland", "United States", "United Kingdom"}
        # Old-but-within-a-week is neutral, not negative — quiet isn't "down".
        assert by_name["United Kingdom"]["changePercent"] == 0.0
        ireland = by_name["Ireland"]
        assert ireland["label"] == "3 stories"
        assert ireland["changePercent"] == 3.0
        us = by_name["United States"]
        assert us["label"] == "1 story"
        assert us["changePercent"] == 0.5
        assert ireland["weight"] > us["weight"]

    async def test_single_cached_feed_is_not_a_map(self, redis: Redis) -> None:
        now = now_ms()
        entry = json.dumps(
            {
                "updated": now,
                "items": [
                    {
                        "id": "i1",
                        "title": "headline",
                        "url": "https://example.com",
                        "pubDate": now - 3_600_000,
                    }
                ],
            }
        )
        await redis.set("news:source:gnews-ie", entry)

        with pytest.raises(OutceptionError) as excinfo:
            await heatmap.get_heatmap(redis, "heatmap-world-buzz")
        assert excinfo.value.status_code == 502

    async def test_view_stamps_demand_for_warmer(self, redis: Redis) -> None:
        with pytest.raises(OutceptionError):
            await heatmap.get_heatmap(redis, "heatmap-world-buzz")

        assert await redis.get("news:heatmap:demand:heatmap-world-buzz")


@pytest.mark.asyncio
class TestFinnhubHeatmaps:
    async def test_hidden_without_api_key(
        self, client: AsyncClient, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "FINNHUB_API_KEY", None)
        response = await client.get("/v1/news/heatmap/heatmap-tech")
        assert response.status_code == 404

    async def test_quotes_and_cached_caps_become_tiles(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "FINNHUB_API_KEY", "test-key")
        spec = heatmap.HeatmapSpec(
            name="Test",
            desc="",
            color="teal",
            provider="finnhub",
            symbols=(("AAPL", "Apple"), ("DEAD", "Dead Co")),
        )
        mocker.patch.dict(heatmap.HEATMAPS, {"heatmap-test": spec})

        async def fake_fetch(url: str, params: dict[str, object]) -> object:
            if params["symbol"] == "DEAD":
                # Finnhub returns zeros for unknown symbols.
                return {"c": 0, "dp": None}
            if "quote" in url:
                return {"c": 123.45, "dp": 1.678}
            return {"marketCapitalization": 3_000_000.0}

        mocker.patch("outception.news.heatmap.fetch_json", side_effect=fake_fetch)

        result = await heatmap.get_heatmap(redis, "heatmap-test")

        assert result["status"] == "success"
        assert result["tiles"] == [
            {
                "symbol": "AAPL",
                "name": "Apple",
                "logo": None,
                "changePercent": 1.68,
                "price": 123.45,
                "weight": 3_000_000.0,
                "url": "https://finance.yahoo.com/quote/AAPL",
            }
        ]
        # The slow-moving profile (cap + logo) is cached for a day.
        cached_profile = await redis.get("news:heatmap:prof:AAPL")
        assert cached_profile is not None
        assert json.loads(cached_profile)["cap"] == 3_000_000.0

    async def test_foreign_currency_caps_convert_to_usd(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "FINNHUB_API_KEY", "test-key")
        spec = heatmap.HeatmapSpec(
            name="Test",
            desc="",
            color="teal",
            provider="finnhub",
            symbols=(("TSM", "TSMC"), ("SQM", "SQM")),
        )
        mocker.patch.dict(heatmap.HEATMAPS, {"heatmap-test": spec})

        async def fake_fetch(
            url: str, params: dict[str, object] | None = None
        ) -> object:
            if "er-api" in url:
                return {"rates": {"TWD": 30.0}}
            if "quote" in url:
                return {"c": 100.0, "dp": 1.0}
            assert params is not None
            if params["symbol"] == "TSM":
                # Finnhub reports the listing-currency cap (TWD millions).
                return {"marketCapitalization": 60_000_000.0, "currency": "TWD"}
            # SQM's known bad row: a CLP-sized cap mislabeled as USD.
            return {"marketCapitalization": 16_996_592.0, "currency": "USD"}

        mocker.patch("outception.news.heatmap.fetch_json", side_effect=fake_fetch)

        result = await heatmap.get_heatmap(redis, "heatmap-test")

        tiles = {tile["symbol"]: tile for tile in result["tiles"]}
        # TWD converted at 30/USD; the implausible "USD" cap is dropped
        # entirely rather than rendered at a made-up size.
        assert set(tiles) == {"TSM"}
        assert tiles["TSM"]["weight"] == 2_000_000.0
