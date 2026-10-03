from outception.cards.deck import (
    DeckData,
    DeckEntry,
    DeckInput,
    always_warm_ids,
    compose_default_deck,
    finalize,
)

KNOWN = {
    "gnews-ie",
    "bbc-world",
    "youtube-guardian",
    "thehill",
    "sport-gaelic-football",
    "sport-hurling",
    "bbcsport",
    "heatmap-ucl",
    "heatmap-premier-league",
    "property-ie",
    "live-quakes",
    "weather",
}

DATA = DeckData(
    base=(
        DeckEntry("bbc-world", inject_after=("youtube-guardian",)),
        DeckEntry("thehill", inject_after=("country:property",)),
        DeckEntry("bbcsport", swap="sports"),
        DeckEntry("heatmap-ucl", swap="sport_tables"),
        DeckEntry("live-quakes", enabled=False),
        DeckEntry("live-storms", season=(6, 11), countries=frozenset({"US"})),
        DeckEntry("weather"),
    ),
    country_tables={
        "IE": {
            "sports": ("sport-gaelic-football", "sport-hurling"),
            "sport_tables": ("heatmap-premier-league",),
            "property": ("property-ie",),
        },
    },
    briefing_profile_by_country={"IE": "sports-fan"},
)


def _input(
    country: str | None,
    *,
    shared_card: str | None = None,
    briefing_enabled: bool = False,
) -> DeckInput:
    return DeckInput(
        country=country,
        month=3,
        known=KNOWN.__contains__,
        disabled=lambda _: False,
        shared_card=shared_card,
        briefing_enabled=briefing_enabled,
    )


def test_country_deck_swaps_and_injects() -> None:
    deck = compose_default_deck(DATA, _input("IE"))
    assert deck == [
        "gnews-ie",
        "bbc-world",
        "youtube-guardian",
        "thehill",
        "property-ie",
        "sport-gaelic-football",
        "sport-hurling",
        "heatmap-premier-league",
        "weather",
    ]


def test_unknown_country_keeps_generic_entries() -> None:
    deck = compose_default_deck(DATA, _input(None))
    assert deck == [
        "bbc-world",
        "youtube-guardian",
        "thehill",
        "bbcsport",
        "heatmap-ucl",
        "weather",
    ]


def test_disabled_season_and_country_gates() -> None:
    us = DeckInput(
        country="US",
        month=7,
        known=lambda i: i in KNOWN or i == "live-storms",
        disabled=lambda _: False,
    )
    assert "live-storms" in compose_default_deck(DATA, us)
    assert "live-quakes" not in compose_default_deck(DATA, us)
    march = DeckInput(
        country="US",
        month=3,
        known=lambda i: i in KNOWN or i == "live-storms",
        disabled=lambda _: False,
    )
    assert "live-storms" not in compose_default_deck(DATA, march)


def test_shared_card_and_briefing_precedence() -> None:
    deck = compose_default_deck(
        DATA, _input("IE", shared_card="thehill", briefing_enabled=True)
    )
    assert deck[:3] == ["thehill", "gnews-ie", "briefing:sports-fan"]
    assert deck.count("thehill") == 1


def test_finalize_drops_disabled_unknown_fallback_and_pins_weather() -> None:
    inp = DeckInput(
        country=None,
        month=1,
        known=KNOWN.__contains__,
        disabled=lambda i: i == "thehill",
        fallback=lambda i: i == "bbcsport",
    )
    assert finalize(
        ["weather", "nope", "thehill", "bbc-world", "bbcsport", "bbc-world"], inp
    ) == ["bbc-world", "weather"]


def test_always_warm_ids() -> None:
    assert always_warm_ids(["a", "b", "c"], ["b", "weather", "d"], head=2) == [
        "a",
        "b",
        "d",
    ]
