"""The live signals, each against a recorded-shape payload, plus the
gating that keeps them dark until the catalog says otherwise."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from google.transit import gtfs_realtime_pb2
from pytest_mock import MockerFixture
from sgp4.api import Satrec

from outception.config import settings
from outception.news import heatmap
from outception.news.catalog import catalog
from outception.news.catalog import registry as catalog_registry
from outception.news.catalog.decks import default_cards, resolve_templates
from outception.news.heatmap.providers.live import (
    iss,
    launches,
    quakes,
    storms,
    transit,
    wildfires,
)
from outception.news.heatmap.providers.live._time import age_label, countdown_label
from outception.redis import Redis

NOW = 1_800_000_000_000  # epoch ms


class TestTime:
    def test_labels(self) -> None:
        assert age_label(NOW - 30_000, NOW) == "just now"
        assert age_label(NOW - 12 * 60_000, NOW) == "12 min ago"
        assert age_label(NOW - 3 * 3_600_000, NOW) == "3 h ago"
        assert age_label(NOW - 2 * 86_400_000, NOW) == "2 d ago"
        assert countdown_label(NOW - 1, NOW) == "now"
        assert countdown_label(NOW + 4 * 60_000, NOW) == "in 4 min"
        assert countdown_label(NOW + (3 * 60 + 10) * 60_000, NOW) == "in 3 h 10 min"
        assert countdown_label(NOW + (2 * 24 + 5) * 3_600_000, NOW) == "in 2 d 5 h"


class TestQuakes:
    def test_tiles_biggest_first_above_the_floor(self) -> None:
        payload = {
            "features": [
                {
                    "properties": {
                        "mag": 4.6,
                        "place": "12 km S of Town",
                        "time": NOW - 3_600_000,
                        "url": "https://earthquake.usgs.gov/e/1",
                    },
                    "geometry": {"coordinates": [-120.0, 36.0, 10.2]},
                },
                {
                    "properties": {
                        "mag": 6.1,
                        "place": "Off the coast",
                        "time": NOW - 7_200_000,
                        "url": "https://earthquake.usgs.gov/e/2",
                    },
                    "geometry": {"coordinates": [140.0, 38.0, 35.0]},
                },
                {
                    "properties": {"mag": 1.2, "place": "too small", "time": NOW},
                    "geometry": {"coordinates": [0, 0, 1]},
                },
                {"properties": {"mag": 3.0, "place": "", "time": NOW}, "geometry": {}},
            ]
        }
        tiles = quakes.tiles_from(payload, now=NOW)
        assert [t["symbol"] for t in tiles] == ["M6.1", "M4.6"]
        assert tiles[0]["subtitle"] == "35 km deep"
        assert tiles[0]["label"] == "2 h ago"
        assert tiles[0]["changePercent"] == -3.0  # the strongest reads reddest
        assert tiles[1]["weight"] == pytest.approx(4.6**2)


class TestStorms:
    def test_strongest_first_and_empty_is_real(self) -> None:
        payload = {
            "activeStorms": [
                {
                    "name": "Alberto",
                    "classification": "Tropical Storm",
                    "intensity": "45",
                    "pressure": "1001",
                    "movementDir": "NW",
                    "movementSpeed": "12",
                },
                {
                    "name": "Beryl",
                    "classification": "Hurricane",
                    "intensity": "110",
                    "pressure": "950",
                    "movementDir": "W",
                    "movementSpeed": "18",
                },
            ]
        }
        tiles = storms.tiles_from(payload)
        assert [t["symbol"] for t in tiles] == ["Beryl", "Alberto"]
        assert tiles[0]["name"] == "Hurricane"
        assert tiles[0]["subtitle"] == "950 mb"
        assert tiles[0]["label"] == "W at 18 kt"
        assert tiles[0]["changePercent"] == -2.75
        assert storms.tiles_from({"activeStorms": []}) == []


class TestWildfires:
    def test_containment_inverts_the_colour(self) -> None:
        payload = {
            "features": [
                {
                    "attributes": {
                        "IncidentName": "Park",
                        "DailyAcres": 42_000,
                        "PercentContained": 25,
                        "POOState": "US-CA",
                        "POOCounty": "Butte",
                        "InciWebUrl": "https://inciweb.wildfire.gov/x",
                    }
                },
                {
                    "attributes": {
                        "IncidentName": "Small",
                        "DailyAcres": 120,
                        "PercentContained": 0,
                    }
                },
                {
                    "attributes": {
                        "IncidentName": "Done",
                        "DailyAcres": 5_000,
                        "PercentContained": 100,
                        "POOState": "US-OR",
                    }
                },
            ]
        }
        tiles = wildfires.tiles_from(payload)
        assert [t["symbol"] for t in tiles] == ["Park", "Done"]
        assert tiles[0]["name"] == "Park Fire"
        assert tiles[0]["subtitle"] == "Butte County, CA"
        assert tiles[0]["label"] == "25% contained"
        assert tiles[0]["changePercent"] == -2.25
        assert tiles[1]["changePercent"] == 0.0


class TestLaunches:
    def test_soonest_first_with_countdowns(self) -> None:
        payload = {
            "results": [
                {
                    "name": "Falcon 9 | Starlink 10-1",
                    "net": "2027-01-16T03:00:00Z",
                    "slug": "falcon-9-starlink",
                    "status": {"abbrev": "Go", "name": "Go for Launch"},
                    "launch_service_provider": {"name": "SpaceX"},
                    "pad": {"location": {"name": "Cape Canaveral"}},
                },
                {
                    "name": "Electron | Owl",
                    "net": "2027-01-15T12:00:00Z",
                    "slug": "electron-owl",
                    "status": {"abbrev": "TBC", "name": "To Be Confirmed"},
                    "launch_service_provider": {"name": "Rocket Lab"},
                    "pad": {},
                },
                {"name": "", "net": "2027-01-15T12:00:00Z"},
            ]
        }
        now = int(datetime(2027, 1, 15, 10, 0, tzinfo=UTC).timestamp() * 1000)
        tiles = launches.tiles_from(payload, now=now)
        assert [t["symbol"] for t in tiles] == ["Owl", "Starlink 10-1"]
        assert tiles[0]["label"] == "in 2 h"
        assert tiles[0]["subtitle"] == "To Be Confirmed"
        assert tiles[1]["subtitle"] == "Go for Launch · Cape Canaveral"
        assert tiles[1]["changePercent"] == 3.0
        assert tiles[1]["url"] == "https://spacelaunchnow.me/launch/falcon-9-starlink"


# A real element set for the station, from a published epoch.
TLE = (
    "1 25544U 98067A   24001.50000000  .00016717  00000-0  10270-3 0  9000",
    "2 25544  51.6400 208.9163 0006703 130.5360 325.0288 15.49500000432000",
)


class TestStationPasses:
    def test_overhead_pass_is_found_and_low_ones_are_not(self) -> None:
        satellite = Satrec.twoline2rv(*TLE)
        start = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
        # The station's ground track in the day after the epoch crosses
        # these latitudes; somewhere along it a city gets a high pass.
        found_any = False
        for lat in (51.5, 40.7, 35.7, -33.9):
            found = iss.next_pass(satellite, lat, 0.0, start, hours=24, step=30)
            if found is not None:
                found_any = True
                assert found["peak"] >= iss.MIN_ELEVATION_DEG
                assert found["duration_s"] > 60
                assert found["direction"] in {
                    "N",
                    "NE",
                    "E",
                    "SE",
                    "S",
                    "SW",
                    "W",
                    "NW",
                }
        assert found_any
        # Nothing at a pole: the orbit never climbs past 52 degrees.
        assert iss.next_pass(satellite, 89.0, 0.0, start, hours=6) is None

    def test_tiles_are_soonest_first(self) -> None:
        cities = [("A", 51.5, -0.1), ("B", 40.7, -74.0), ("C", -33.9, 151.2)]
        tiles = iss.tiles_from(TLE, cities, now=datetime(2024, 1, 1, 12, 0, tzinfo=UTC))
        assert tiles
        labels = [t["label"] for t in tiles]
        assert all(label.startswith("in ") for label in labels)
        assert all("peaks" in str(t["subtitle"]) for t in tiles)

    def test_parse_tle(self) -> None:
        assert iss.parse_tle("ISS (ZARYA)\n" + "\n".join(TLE) + "\n") == TLE
        with pytest.raises(Exception, match="orbital elements"):
            iss.parse_tle("nothing here")

    def test_covered_cities_come_from_the_capitals(self) -> None:
        names = [name for name, _, _ in iss.covered_cities()]
        assert "London" in names
        assert len(names) >= 25


def _alert_feed() -> bytes:
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    now = int(datetime.now(UTC).timestamp())
    entity = feed.entity.add()
    entity.id = "1"
    entity.alert.header_text.translation.add(
        text="Signal problems at Central", language="en"
    )
    entity.alert.informed_entity.add(route_id="A")
    entity.alert.informed_entity.add(route_id="C")
    period = entity.alert.active_period.add()
    period.start = now - 1800
    entity.alert.severity_level = 4  # SEVERE
    later = feed.entity.add()
    later.id = "2"
    later.alert.header_text.translation.add(
        text="Planned work next month", language="en"
    )
    period = later.alert.active_period.add()
    period.start = now + 30 * 86400
    return feed.SerializeToString()


class TestTransit:
    def test_line_status_only_reports_disruption(self) -> None:
        payload = [
            {
                "name": "Central",
                "lineStatuses": [
                    {
                        "statusSeverity": 6,
                        "statusSeverityDescription": "Minor Delays",
                        "reason": "Central Line: Minor delays due to a signal failure.",
                    }
                ],
            },
            {
                "name": "Victoria",
                "lineStatuses": [
                    {"statusSeverity": 10, "statusSeverityDescription": "Good Service"}
                ],
            },
            {
                "name": "Jubilee",
                "lineStatuses": [
                    {
                        "statusSeverity": 2,
                        "statusSeverityDescription": "Suspended",
                        "reason": "Jubilee: Suspended.",
                    }
                ],
            },
        ]
        tiles = transit.LineStatusAdapter().parse(payload)
        assert [t["label"] for t in tiles] == ["Jubilee", "Central"]
        assert tiles[0]["name"] == "Suspended"
        assert tiles[0]["changePercent"] == -3.0
        assert tiles[1]["subtitle"] == "Minor delays due to a signal failure."
        assert transit.LineStatusAdapter().parse(payload[1:2]) == []

    def test_gtfs_alerts_skip_future_ones(self) -> None:
        tiles = transit.GtfsAlertsAdapter("https://agency.example").parse(_alert_feed())
        assert len(tiles) == 1
        tile = tiles[0]
        assert tile["name"] == "Signal problems at Central"
        assert tile["symbol"] == "2 lines"
        assert tile["subtitle"] == "A, C"
        assert tile["changePercent"] == -3.0
        assert tile["label"] == "30 min ago"
        assert tile["url"] == "https://agency.example"

    @pytest.mark.asyncio
    async def test_keyed_agency_without_a_key_fails_cleanly(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "TRANSIT_KEY_NEWYORK", None)
        spec = heatmap.HEATMAPS["transit-newyork"]
        with pytest.raises(Exception, match="registration key"):
            await transit.fetch_tiles(redis, spec)

    @pytest.mark.asyncio
    async def test_keyed_agency_sends_its_header(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(settings, "TRANSIT_KEY_SYDNEY", "k")
        fetch = mocker.patch(
            "outception.news.heatmap.providers.http.fetch_bytes",
            AsyncMock(return_value=_alert_feed()),
        )
        tiles = await transit.fetch_tiles(redis, heatmap.HEATMAPS["transit-sydney"])
        assert len(tiles) == 1
        assert fetch.call_args.kwargs["headers"] == {"Authorization": "apikey k"}


@pytest.mark.asyncio
class TestGating:
    async def test_dark_signals_stay_out_of_the_roster_and_decks(self) -> None:
        registry = catalog_registry()
        for signal in catalog().live_signals:
            assert not signal.enabled
            assert signal.id not in registry.rows
            assert heatmap.HEATMAPS[signal.id].live
            assert signal.id not in heatmap.available_heatmap_ids()
        for country in ("US", "GB", None):
            deck = default_cards(registry, country, month=8)
            assert not any(
                card_id.startswith(("live-", "transit-")) for card_id in deck
            )
        for template in resolve_templates(registry, "US"):
            assert not any(sid.startswith("live-") for sid in template["sources"])

    async def test_enabled_signal_serves_an_empty_feed_as_a_real_answer(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        spec = heatmap.HEATMAPS["live-storms"]
        mocker.patch.dict(
            heatmap.HEATMAPS,
            {"live-storms": spec.__class__(**{**spec.__dict__, "enabled": True})},
        )
        mocker.patch(
            "outception.news.heatmap.providers.http.fetch_json",
            AsyncMock(return_value={"activeStorms": []}),
        )
        result = await heatmap.get_heatmap(redis, "live-storms")
        assert result["status"] == "success"
        assert result["tiles"] == []

    async def test_poller_refreshes_only_enabled_stale_signals(
        self, redis: Redis, mocker: MockerFixture
    ) -> None:
        from outception.news import tasks

        mocker.patch("outception.news.tasks.create_redis", return_value=redis)
        mocker.patch.object(redis, "close", AsyncMock())
        quakes_spec = heatmap.HEATMAPS["live-quakes"]
        mocker.patch.dict(
            heatmap.HEATMAPS,
            {
                "live-quakes": quakes_spec.__class__(
                    **{**quakes_spec.__dict__, "enabled": True}
                )
            },
        )
        fetch = mocker.patch(
            "outception.news.heatmap.providers.http.fetch_json",
            AsyncMock(return_value={"features": []}),
        )
        await tasks.poll_live_signals()
        assert fetch.call_count == 1  # the one enabled signal, nothing else
        await tasks.poll_live_signals()
        assert fetch.call_count == 1  # fresh now: not polled again
