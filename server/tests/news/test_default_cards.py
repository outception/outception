import pytest
from httpx import AsyncClient

from outception.cards.kinds import WEATHER_STRIP_ID
from outception.news.catalog import registry as catalog_registry
from outception.news.registry import DISABLED_SOURCES, SOURCES


@pytest.mark.asyncio
class TestDefaultCards:
    async def test_returns_the_category_cards(self, client: AsyncClient) -> None:
        body = (await client.get("/v1/news/default-cards")).json()
        # The trust anchors travel as pairs: a wall card and a video companion
        # from a different brand each.
        assert body[:4] == ["bbc-world", "youtube-guardian", "nytimes", "youtube-cnn"]
        # The science block lands right after the politics pair; the podcast
        # beat sits after the crypto map, which sits beside its news card.
        assert body.index("sci-scientificprogress") == body.index("propublica") + 1
        assert body.index("podcast-tedtalksdaily") == body.index("heatmap-crypto") + 1
        assert body.index("heatmap-crypto") == body.index("coindesk") + 1
        assert "legalsportsreport" in body
        assert body[-1] == WEATHER_STRIP_ID
        assert len(body) == len(set(body))
        # The playable breaks of the old wall are gone: no game ids anywhere.
        assert not {"crossword", "sudoku", "solitaire", "cube"} & set(body)

    async def test_country_swaps_the_sports_slice(self, client: AsyncClient) -> None:
        ie = (
            await client.get("/v1/news/default-cards", params={"country": "IE"})
        ).json()
        assert ie[0] == "gnews-ie"
        assert "sport-gaelic-football" in ie
        assert "sport-hurling" in ie
        assert "bbcsport" not in ie
        us = (
            await client.get("/v1/news/default-cards", params={"country": "US"})
        ).json()
        assert "sport-nfl" in us
        assert "sport-nba" in us

    async def test_country_swaps_the_sports_heatmap(self, client: AsyncClient) -> None:
        us = (
            await client.get("/v1/news/default-cards", params={"country": "US"})
        ).json()
        assert "heatmap-ucl" not in us
        assert "heatmap-nfl" in us
        assert "heatmap-nba" in us
        india = (
            await client.get("/v1/news/default-cards", params={"country": "IN"})
        ).json()
        assert "heatmap-ucl" not in india

    async def test_unmapped_country_keeps_generic_cards(
        self, client: AsyncClient
    ) -> None:
        body = (
            await client.get("/v1/news/default-cards", params={"country": "ZZ"})
        ).json()
        generic = (await client.get("/v1/news/default-cards")).json()
        assert body == generic


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
        for sid in ("deals-pe", "property-pe", "events-pe", "business-pe", "health-pe"):
            assert sid in cards, sid


def test_every_base_entry_exists_and_is_enabled() -> None:
    from outception.news.heatmap import HEATMAPS

    for entry in catalog_registry().catalog.deck.base:
        sid = entry.id
        if sid == WEATHER_STRIP_ID or sid in HEATMAPS:
            continue
        assert sid in SOURCES, f"{sid} missing from the catalog"
        assert sid not in DISABLED_SOURCES, f"{sid} is disabled"


def test_every_country_pick_exists_and_is_enabled() -> None:
    # Table cards are key-gated: absent from the roster without their
    # provider keys, as in this environment, so only their spec is checked.
    from outception.news.heatmap import HEATMAPS

    tables = catalog_registry().catalog.country_tables
    for country, by_table in tables.items():
        for table, ids in by_table.items():
            for sid in ids:
                if sid in HEATMAPS:
                    continue
                assert sid in SOURCES, (country, table, sid)
                assert sid not in DISABLED_SOURCES, (country, table, sid)
