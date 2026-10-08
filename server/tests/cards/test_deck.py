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
)


def _input(
    country: str | None,
    *,
    shared_card: str | None = None,
) -> DeckInput:
    return DeckInput(
        country=country,
        month=3,
        known=KNOWN.__contains__,
        disabled=lambda _: False,
        shared_card=shared_card,
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


def test_shared_card_precedence() -> None:
    deck = compose_default_deck(DATA, _input("IE", shared_card="thehill"))
    assert deck[:3] == ["thehill", "gnews-ie", "bbc-world"]
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


def test_shared_fixture_parity() -> None:
    """The composer reproduces every case of the fixture the client composer
    is tested against, so both produce the same deck for the same inputs."""
    import json
    from pathlib import Path

    fixture = json.loads(
        (Path(__file__).parent / "fixtures" / "compose.json").read_text()
    )
    raw = fixture["data"]
    data = DeckData(
        base=tuple(
            DeckEntry(
                entry["id"],
                inject_after=tuple(entry.get("injectAfter", ())),
                swap=entry.get("swap"),
                enabled=entry.get("enabled", True),
                season=tuple(entry["season"]) if entry.get("season") else None,
                countries=(
                    frozenset(entry["countries"]) if entry.get("countries") else None
                ),
            )
            for entry in raw["base"]
        ),
        country_tables={
            country: {name: tuple(ids) for name, ids in tables.items()}
            for country, tables in raw["countryTables"].items()
        },
    )
    assert len(fixture["cases"]) >= 8
    for case in fixture["cases"]:
        spec = case["input"]
        inp = DeckInput(
            country=spec["country"],
            month=spec["month"],
            known=set(spec["known"]).__contains__,
            disabled=set(spec["disabled"]).__contains__,
            fallback=set(spec["fallback"]).__contains__,
            shared_card=spec["sharedCard"],
        )
        assert compose_default_deck(data, inp) == case["expected"], case["name"]
