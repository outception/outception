from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from pytest_mock import MockerFixture

from outception.news import cities


class TestNormalise:
    def test_folds_accents_punctuation_and_the_city_suffix(self) -> None:
        assert cities.normalize_toponym("São Paulo") == "sao paulo"
        assert cities.normalize_toponym("  New-York City ") == "new york"
        assert cities.normalize_toponym("DUBLIN") == "dublin"
        assert cities.normalize_toponym("City") == "city"


class TestKnownCards:
    def test_matches_a_known_city_by_name(self) -> None:
        assert cities.match_city_card("Dublin") == "city-ireland-dublin"
        assert cities.match_city_card("new york") == "city-unitedstates-newyork"

    def test_ambiguous_prefix_returns_nothing(self) -> None:
        assert cities.match_city_card("s") is None
        assert cities.match_city_card("zzzz") is None

    def test_nearest_card_within_reach(self) -> None:
        grid = {"a": (53.35, -6.26), "b": (51.51, -0.13)}
        assert cities.nearest_city_card(53.46, -6.22, grid) == "a"
        assert cities.nearest_city_card(48.85, 2.35, grid) is None
        assert cities.nearest_city_card(53.46, -6.22, grid, within_km=5) is None


@pytest.mark.asyncio
class TestResolveEndpoint:
    async def test_known_city_needs_no_network(
        self, client: AsyncClient, mocker: MockerFixture
    ) -> None:
        fetch = mocker.patch("outception.news.cities.fetch_json", AsyncMock())
        body = (await client.get("/v1/news/cities", params={"q": "Dublin"})).json()
        assert body["cardId"] == "city-ireland-dublin"
        # The place comes from the catalog: a name and the coordinates the
        # nearest-card lookup keeps, so the weather tool needs no geocoder.
        assert body["place"]["name"]
        assert 50 < body["place"]["latitude"] < 56
        assert -8 < body["place"]["longitude"] < -5
        fetch.assert_not_called()

    async def test_geocodes_and_lands_on_the_nearest_card(
        self, client: AsyncClient, mocker: MockerFixture
    ) -> None:
        mocker.patch(
            "outception.news.cities.fetch_json",
            AsyncMock(
                return_value={
                    "results": [
                        {
                            "name": "Swords",
                            "admin1": "Leinster",
                            "country": "Ireland",
                            "country_code": "IE",
                            "latitude": 53.46,
                            "longitude": -6.22,
                        }
                    ]
                }
            ),
        )
        body = (await client.get("/v1/news/cities", params={"q": "Swords"})).json()
        assert body["cardId"] == "city-ireland-dublin"
        assert body["place"]["name"] == "Swords"
        assert body["place"]["country"] == "Ireland"

    async def test_misses_are_remembered(
        self, client: AsyncClient, mocker: MockerFixture
    ) -> None:
        fetch = mocker.patch(
            "outception.news.cities.fetch_json", AsyncMock(return_value={"results": []})
        )
        first = (
            await client.get("/v1/news/cities", params={"q": "Nowhereville"})
        ).json()
        second = (
            await client.get("/v1/news/cities", params={"q": "nowhereville"})
        ).json()
        assert first["cardId"] is None
        assert first["place"] is None
        assert second["cardId"] is None
        assert second["place"] is None
        assert fetch.await_count == 1
