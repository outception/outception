import pytest
from httpx import AsyncClient

from outception.news.endpoints import DEFAULT_DECK, WEATHER_DECK_ID
from outception.news.metadata import SOURCES
from outception.news.registry import DISABLED_SOURCES


@pytest.mark.asyncio
class TestDefaultDeck:
    async def test_returns_the_category_deck(self, client: AsyncClient) -> None:
        body = (await client.get("/v1/news/default-deck")).json()
        # One representative source per category, in order.
        assert body == list(DEFAULT_DECK)
        assert body[0] == "bbc-world"  # World leads
        assert "coindesk" in body  # Crypto
        assert "legalsportsreport" in body  # Betting
        assert WEATHER_DECK_ID in body  # synthetic weather card rides along

    async def test_country_swaps_the_sports_slice(self, client: AsyncClient) -> None:
        # A known country swaps the generic sports sources for its native ones.
        ie = (
            await client.get("/v1/news/default-deck", params={"country": "IE"})
        ).json()
        assert "sport-gaelic-football" in ie
        assert "sport-hurling" in ie
        assert "bbcsport" not in ie  # generic sports swapped out
        us = (
            await client.get("/v1/news/default-deck", params={"country": "US"})
        ).json()
        assert "sport-nfl" in us
        assert "sport-nba" in us

    async def test_unmapped_country_keeps_generic_deck(
        self, client: AsyncClient
    ) -> None:
        # A country we don't map falls back to the generic, location-free deck.
        body = (
            await client.get("/v1/news/default-deck", params={"country": "ZZ"})
        ).json()
        assert body == list(DEFAULT_DECK)

    def test_every_deck_source_exists_and_is_enabled(self) -> None:
        # The weather card is synthetic (no roster row); every other entry must
        # be a real, enabled source.
        for sid in DEFAULT_DECK:
            if sid == WEATHER_DECK_ID:
                continue
            assert sid in SOURCES, f"{sid} missing from the roster"
            assert sid not in DISABLED_SOURCES, f"{sid} is disabled"


@pytest.mark.asyncio
class TestCountrySeeding:
    async def test_country_seeds_deals_property_travel(
        self, client: AsyncClient
    ) -> None:
        response = await client.get("/v1/news/default-deck", params={"country": "GB"})
        deck = response.json()
        assert "hotukdeals" in deck
        assert "propertyindustryeye" in deck
        assert "holidaypirates" in deck

    async def test_english_market_seeds_kickstarter(self, client: AsyncClient) -> None:
        for cc in ("US", "GB", "IE"):
            deck = (
                await client.get("/v1/news/default-deck", params={"country": cc})
            ).json()
            assert "kickstarter" in deck, cc

    async def test_non_english_market_localises_without_kickstarter(
        self, client: AsyncClient
    ) -> None:
        deck = (
            await client.get("/v1/news/default-deck", params={"country": "DE"})
        ).json()
        assert "kickstarter" not in deck
        assert "mydealz" in deck
        assert "property-de" in deck
        assert "urlaubspiraten" in deck

    async def test_fallback_market_gets_generated_searches(
        self, client: AsyncClient
    ) -> None:
        deck = (
            await client.get("/v1/news/default-deck", params={"country": "PE"})
        ).json()
        assert "deals-pe" in deck
        assert "property-pe" in deck

    async def test_every_country_pick_exists_and_is_enabled(self) -> None:
        from outception.news.shopping_data import (
            COUNTRY_DEALS,
            COUNTRY_PROPERTY,
            COUNTRY_TRAVEL,
        )

        picks = (
            set(COUNTRY_DEALS.values())
            | set(COUNTRY_PROPERTY.values())
            | set(COUNTRY_TRAVEL.values())
        )
        for sid in picks:
            assert sid in SOURCES, sid
            assert sid not in DISABLED_SOURCES, sid
