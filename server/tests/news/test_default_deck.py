import pytest
from httpx import AsyncClient

from outception.news.endpoints import DEFAULT_DECK, DEFAULT_PODCAST, WEATHER_DECK_ID
from outception.news.metadata import SOURCES
from outception.news.registry import DISABLED_SOURCES


def _with_games(deck: list[str]) -> list[str]:
    """Mirror the endpoint's playable-break placement: quarter marks of the
    finished deck, with the cube closing ahead of the pinned weather card."""
    has_weather = bool(deck) and deck[-1] == WEATHER_DECK_ID
    content = deck[:-1] if has_weather else deck[:]
    n = len(content)
    for offset, game in enumerate(("crossword", "sudoku", "solitaire")):
        content.insert(round(n * (offset + 1) / 4) + offset, game)
    content.append("cube")
    if has_weather:
        content.append(WEATHER_DECK_ID)
    return content


@pytest.mark.asyncio
class TestDefaultDeck:
    async def test_returns_the_category_deck(self, client: AsyncClient) -> None:
        body = (await client.get("/v1/news/default-deck")).json()
        # One representative source per category, in order. Key-gated heatmap
        # cards drop out server-side when their provider keys are unset (as in
        # this test environment).
        head = ["bbc-world", "youtube-guardian", "nytimes", "youtube-cnn"]
        science_block = [
            "sci-scientificprogress",
            "youtube-veritasium",
            "sci-spacediscoveries",
            "sci-medicalprogress",
            "sci-fusionprogress",
            "sci-airbornewindenergy",
        ]
        rest: list[str] = []
        for sid in DEFAULT_DECK:
            if sid in head:
                continue
            rest.append(sid)
            if sid == "propublica":
                rest.extend(science_block)
            if sid == "heatmap-crypto":
                rest.append(DEFAULT_PODCAST)
        expected = _with_games(
            [sid for sid in head + rest if sid in SOURCES or sid == WEATHER_DECK_ID]
        )
        assert body == expected
        assert body[0] == "bbc-world"  # the trust anchor leads
        assert body[1] == "youtube-guardian"  # cross-brand video companion
        assert body[2] == "nytimes"  # the second trust anchor pair
        assert body[3] == "youtube-cnn"
        # The science/bombshell block lands right after the politics pair;
        # the podcast beat sits after the crypto map.
        assert body.index("sci-scientificprogress") == body.index("propublica") + 1
        assert body.index(DEFAULT_PODCAST) == body.index("heatmap-crypto") + 1
        # Heatmaps sit beside their related news, not in the head.
        assert body.index("heatmap-crypto") == body.index("coindesk") + 1
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

    async def test_country_swaps_the_sports_heatmap(self, client: AsyncClient) -> None:
        # The sports heat grid localises like the sports sources: US visitors
        # get the NFL/NBA grids instead of the Champions League one. (Cricket
        # and soccer-league grids are key-gated, so they only assert absence of
        # the generic UCL grid here.)
        us = (
            await client.get("/v1/news/default-deck", params={"country": "US"})
        ).json()
        assert "heatmap-ucl" not in us
        assert "heatmap-nfl" in us
        assert "heatmap-nba" in us
        de = (
            await client.get("/v1/news/default-deck", params={"country": "IN"})
        ).json()
        assert "heatmap-ucl" not in de

    async def test_unmapped_country_keeps_generic_deck(
        self, client: AsyncClient
    ) -> None:
        # A country we don't map falls back to the generic, location-free deck.
        body = (
            await client.get("/v1/news/default-deck", params={"country": "ZZ"})
        ).json()
        head = ["bbc-world", "youtube-guardian", "nytimes", "youtube-cnn"]
        science_block = [
            "sci-scientificprogress",
            "youtube-veritasium",
            "sci-spacediscoveries",
            "sci-medicalprogress",
            "sci-fusionprogress",
            "sci-airbornewindenergy",
        ]
        rest: list[str] = []
        for sid in DEFAULT_DECK:
            if sid in head:
                continue
            rest.append(sid)
            if sid == "propublica":
                rest.extend(science_block)
            if sid == "heatmap-crypto":
                rest.append(DEFAULT_PODCAST)
        expected = _with_games(
            [sid for sid in head + rest if sid in SOURCES or sid == WEATHER_DECK_ID]
        )
        assert body == expected

    def test_every_deck_source_exists_and_is_enabled(self) -> None:
        # The weather card is synthetic (no roster row); heatmap cards are
        # key-gated (absent from the roster without provider keys — clients
        # drop unresolvable deck ids); every other entry must be a real,
        # enabled source.
        from outception.news.heatmap import HEATMAPS

        for sid in DEFAULT_DECK:
            if sid == WEATHER_DECK_ID:
                continue
            if sid in HEATMAPS:
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
        assert "headforpoints" in deck
        assert "events-gb" in deck
        assert "business-gb" in deck
        assert "health-gb" in deck

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
        assert "events-pe" in deck
        assert "business-pe" in deck
        assert "health-pe" in deck

    async def test_every_country_pick_exists_and_is_enabled(self) -> None:
        from outception.news.shopping_data import (
            COUNTRY_DEALS,
            COUNTRY_EVENTS,
            COUNTRY_PROPERTY,
            COUNTRY_TRAVEL,
        )

        picks = (
            set(COUNTRY_DEALS.values())
            | set(COUNTRY_PROPERTY.values())
            | set(COUNTRY_TRAVEL.values())
            | set(COUNTRY_EVENTS.values())
        )
        for sid in picks:
            assert sid in SOURCES, sid
            assert sid not in DISABLED_SOURCES, sid
