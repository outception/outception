from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from pytest_mock import MockerFixture

from outception.news import weather
from outception.news.fetch import NewsFetchError

_OPEN_METEO = {
    "timezone": "Europe/London",
    "current": {
        "temperature_2m": 14.2,
        "relative_humidity_2m": 72,
        "apparent_temperature": 12.1,
        "is_day": 1,
        "weather_code": 3,
        "wind_speed_10m": 18.5,
    },
    "daily": {
        "time": ["2026-07-16", "2026-07-17", "2026-07-18", "2026-07-19"],
        "weather_code": [3, 61, 0, 2],
        "temperature_2m_max": [16.0, 15.0, 20.0, 18.0],
        "temperature_2m_min": [9.0, 10.0, 11.0, 10.5],
    },
}


class TestResolveLocation:
    def test_precise_coordinates_win(self) -> None:
        name, lat, lon = weather.resolve_location(35.6, 139.7, "GB")
        assert name is None  # filled from the upstream timezone
        assert (lat, lon) == (35.6, 139.7)

    def test_falls_back_to_country_capital(self) -> None:
        name, lat, lon = weather.resolve_location(None, None, "jp")
        assert name == "Tokyo"
        assert (lat, lon) == (35.6762, 139.6503)

    def test_unmapped_country_uses_global_default(self) -> None:
        assert weather.resolve_location(None, None, "ZZ")[0] == "London"

    def test_no_location_uses_global_default(self) -> None:
        assert weather.resolve_location(None, None, None)[0] == "London"


class TestCapitalCoverage:
    def test_covers_every_continent_and_the_long_tail(self) -> None:
        # A spread of large countries, small states, and territories that must
        # all resolve to a real capital rather than the London default (none of
        # these is GB, so "London" here would mean a miss).
        for code in ("FR", "NG", "BR", "IN", "TV", "XK", "VA", "GL", "FM", "SS"):
            assert weather.resolve_location(None, None, code)[0] != "London"

    def test_broad_iso_coverage(self) -> None:
        # Comprehensive map — every UN member plus observers and the inhabited
        # territories Cloudflare emits (~230 codes).
        assert len(weather._CAPITALS) >= 200

    def test_all_entries_are_well_formed(self) -> None:
        for code, (name, lat, lon) in weather._CAPITALS.items():
            assert len(code) == 2, code
            assert code.isupper(), code
            assert name.strip(), code
            assert -90.0 <= lat <= 90.0, code
            assert -180.0 <= lon <= 180.0, code


@pytest.mark.asyncio
class TestWeatherEndpoint:
    async def test_precise_coords_name_from_timezone(
        self, client: AsyncClient, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(weather, "_fetch", AsyncMock(return_value=_OPEN_METEO))
        response = await client.get(
            "/v1/news/weather", params={"latitude": 51.5, "longitude": -0.12}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["location"] == "London"  # from "Europe/London"
        assert body["current"]["temperature"] == 14.2
        assert body["current"]["weatherCode"] == 3
        assert body["current"]["isDay"] is True
        assert len(body["daily"]) == 4
        assert body["daily"][0]["tempMax"] == 16.0

    async def test_country_fallback_uses_capital_name(
        self, client: AsyncClient, mocker: MockerFixture
    ) -> None:
        fetch = mocker.patch.object(
            weather, "_fetch", AsyncMock(return_value=_OPEN_METEO)
        )
        response = await client.get("/v1/news/weather", params={"country": "JP"})
        assert response.status_code == 200
        assert response.json()["location"] == "Tokyo"
        # Tokyo's capital coordinates were passed to the upstream, not London's.
        assert fetch.await_args is not None
        assert fetch.await_args.args == (35.6762, 139.6503)

    async def test_second_request_served_from_cache(
        self, client: AsyncClient, mocker: MockerFixture
    ) -> None:
        fetch = mocker.patch.object(
            weather, "_fetch", AsyncMock(return_value=_OPEN_METEO)
        )
        params = {"latitude": 51.5, "longitude": -0.12}
        await client.get("/v1/news/weather", params=params)
        await client.get("/v1/news/weather", params=params)
        fetch.assert_awaited_once()  # rounded coords hit the same cache key

    async def test_upstream_failure_on_cold_cache_is_502(
        self, client: AsyncClient, mocker: MockerFixture
    ) -> None:
        mocker.patch.object(
            weather,
            "_fetch",
            AsyncMock(side_effect=NewsFetchError("boom")),
        )
        response = await client.get(
            "/v1/news/weather", params={"latitude": 1.0, "longitude": 2.0}
        )
        assert response.status_code == 502

    async def test_invalid_coordinates_rejected(self, client: AsyncClient) -> None:
        response = await client.get(
            "/v1/news/weather", params={"latitude": 999, "longitude": 0}
        )
        assert response.status_code == 422
