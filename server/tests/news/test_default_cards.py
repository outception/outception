import pytest
from httpx import AsyncClient

from outception.news.endpoints import DEFAULT_CARDS, DEFAULT_PODCAST, WEATHER_CARD_ID
from outception.news.metadata import SOURCES
from outception.news.registry import DISABLED_SOURCES


def _with_games(cards: list[str]) -> list[str]:
    """Mirror the endpoint's playable-break placement: quarter marks of the
    finished cards, with the cube closing ahead of the pinned weather card."""
    has_weather = bool(cards) and cards[-1] == WEATHER_CARD_ID
    content = cards[:-1] if has_weather else cards[:]
    n = len(content)
    for offset, game in enumerate(("crossword", "sudoku", "solitaire")):
        content.insert(round(n * (offset + 1) / 4) + offset, game)
    content.append("cube")
    if has_weather:
        content.append(WEATHER_CARD_ID)
    return content


@pytest.mark.asyncio
class TestDefaultCards:
    async def test_returns_the_category_cards(self, client: AsyncClient) -> None:
        body = (await client.get("/v1/news/default-cards")).json()
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
        for sid in DEFAULT_CARDS:
            if sid in head:
                continue
            rest.append(sid)
            if sid == "propublica":
                rest.extend(science_block)
            if sid == "heatmap-crypto":
                rest.append(DEFAULT_PODCAST)
        expected = _with_games(
            [sid for sid in head + rest if sid in SOURCES or sid == WEATHER_CARD_ID]
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
        assert WEATHER_CARD_ID in body  # synthetic weather card rides along

    async def test_country_swaps_the_sports_slice(self, client: AsyncClient) -> None:
        # A known country swaps the generic sports sources for its native ones.
        ie = (
            await client.get("/v1/news/default-cards", params={"country": "IE"})
        ).json()
        assert "sport-gaelic-football" in ie
        assert "sport-hurling" in ie
        assert "bbcsport" not in ie  # generic sports swapped out
        us = (
            await client.get("/v1/news/default-cards", params={"country": "US"})
        ).json()
        assert "sport-nfl" in us
        assert "sport-nba" in us

    async def test_country_swaps_the_sports_heatmap(self, client: AsyncClient) -> None:
        # The sports heat grid localises like the sports sources: US visitors
        # get the NFL/NBA grids instead of the Champions League one. (Cricket
        # and soccer-league grids are key-gated, so they only assert absence of
        # the generic UCL grid here.)
        us = (
            await client.get("/v1/news/default-cards", params={"country": "US"})
        ).json()
        assert "heatmap-ucl" not in us
        assert "heatmap-nfl" in us
        assert "heatmap-nba" in us
        de = (
            await client.get("/v1/news/default-cards", params={"country": "IN"})
        ).json()
        assert "heatmap-ucl" not in de

    async def test_unmapped_country_keeps_generic_cards(
        self, client: AsyncClient
    ) -> None:
        # A country we don't map falls back to the generic, location-free card set.
        body = (
            await client.get("/v1/news/default-cards", params={"country": "ZZ"})
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
        for sid in DEFAULT_CARDS:
            if sid in head:
                continue
            rest.append(sid)
            if sid == "propublica":
                rest.extend(science_block)
            if sid == "heatmap-crypto":
                rest.append(DEFAULT_PODCAST)
        expected = _with_games(
            [sid for sid in head + rest if sid in SOURCES or sid == WEATHER_CARD_ID]
        )
        assert body == expected

    def test_every_card_source_exists_and_is_enabled(self) -> None:
        # The weather card is synthetic (no roster row); heatmap cards are
        # key-gated (absent from the roster without provider keys - clients
        # drop unresolvable card set ids); every other entry must be a real,
        # enabled source.
        from outception.news.heatmap import HEATMAPS

        for sid in DEFAULT_CARDS:
            if sid == WEATHER_CARD_ID:
                continue
            if sid in HEATMAPS:
                continue
            assert sid in SOURCES, f"{sid} missing from the roster"
            assert sid not in DISABLED_SOURCES, f"{sid} is disabled"


@pytest.mark.asyncio
class TestLegacyPath:
    async def test_old_path_still_answers(self, client: AsyncClient) -> None:
        """Readers on 1.7.x ask for /default-deck and a store update reaches
        them slowly, so the old path must keep returning the same body."""
        legacy = await client.get("/v1/news/default-deck")
        current = await client.get("/v1/news/default-cards")
        assert legacy.status_code == 200
        assert legacy.json() == current.json()


@pytest.mark.asyncio
class TestCountrySeeding:
    async def test_country_seeds_deals_property_travel(
        self, client: AsyncClient
    ) -> None:
        response = await client.get("/v1/news/default-cards", params={"country": "GB"})
        cards = response.json()
        assert "hotukdeals" in cards
        assert "propertyindustryeye" in cards
        assert "headforpoints" in cards
        assert "events-gb" in cards
        assert "business-gb" in cards
        assert "health-gb" in cards

    async def test_english_market_seeds_kickstarter(self, client: AsyncClient) -> None:
        for cc in ("US", "GB", "IE"):
            cards = (
                await client.get("/v1/news/default-cards", params={"country": cc})
            ).json()
            assert "kickstarter" in cards, cc

    async def test_non_english_market_localises_without_kickstarter(
        self, client: AsyncClient
    ) -> None:
        cards = (
            await client.get("/v1/news/default-cards", params={"country": "DE"})
        ).json()
        assert "kickstarter" not in cards
        assert "mydealz" in cards
        assert "property-de" in cards
        assert "urlaubspiraten" in cards

    async def test_fallback_market_gets_generated_searches(
        self, client: AsyncClient
    ) -> None:
        cards = (
            await client.get("/v1/news/default-cards", params={"country": "PE"})
        ).json()
        assert "deals-pe" in cards
        assert "property-pe" in cards
        assert "events-pe" in cards
        assert "business-pe" in cards
        assert "health-pe" in cards

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
