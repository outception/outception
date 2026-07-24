import pytest
from httpx import AsyncClient

from outception.news.endpoints import DEFAULT_DECK, DISABLED_SOURCES, WEATHER_DECK_ID
from outception.news.metadata import SOURCES


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

    async def test_is_location_independent(self, client: AsyncClient) -> None:
        # The deck must be the same regardless of the reader's country.
        a = (
            await client.get("/v1/news/default-deck", headers={"CF-IPCountry": "JP"})
        ).json()
        b = (
            await client.get("/v1/news/default-deck", headers={"CF-IPCountry": "DE"})
        ).json()
        assert a == b == list(DEFAULT_DECK)

    def test_every_deck_source_exists_and_is_enabled(self) -> None:
        # The weather card is synthetic (no roster row); every other entry must
        # be a real, enabled source.
        for sid in DEFAULT_DECK:
            if sid == WEATHER_DECK_ID:
                continue
            assert sid in SOURCES, f"{sid} missing from the roster"
            assert sid not in DISABLED_SOURCES, f"{sid} is disabled"
