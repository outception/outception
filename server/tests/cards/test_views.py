from outception.cards.kinds import CardKind, kind_for_id, kind_for_type
from outception.cards.schemas import Card, CardItem, FeedPayload, TablePayload
from outception.cards.views import to_heatmap_response, to_source_response
from outception.net.state import SignalState
from outception.news.schemas import HeatmapTile, SourceMeta

META = SourceMeta(
    id="bbc-world", name="BBC World", color="#000", column="world", interval=600000
)


def test_kinds() -> None:
    assert kind_for_type(None) == CardKind.feed
    assert kind_for_type("heatmap") == CardKind.table
    assert kind_for_id("weather") == CardKind.strip
    assert kind_for_id("bbc-world") == CardKind.feed


def test_feed_card_maps_to_legacy_response_without_envelope_fields() -> None:
    card = Card(
        id="bbc-world",
        kind=CardKind.feed,
        meta=META,
        state=SignalState.nominal,
        updated_at=1700000000000,
        payload=FeedPayload(
            items=[
                CardItem(
                    id="1",
                    title="Headline",
                    url="https://example.com/a",
                    cluster_id="c1",
                    publisher_count=4,
                )
            ]
        ),
    )
    legacy = to_source_response(card)
    assert legacy.status == "success"
    assert legacy.updated_time == 1700000000000
    wire = legacy.model_dump(by_alias=True)
    assert wire["items"][0] == {
        "id": "1",
        "title": "Headline",
        "url": "https://example.com/a",
        "mobileUrl": None,
        "pubDate": None,
        "extra": None,
    }
    assert "clusterId" not in wire["items"][0]


def test_non_nominal_state_is_cache() -> None:
    card = Card(
        id="bbc-world",
        kind=CardKind.feed,
        meta=META,
        state=SignalState.stale,
        updated_at=1,
        payload=FeedPayload(items=[]),
    )
    assert to_source_response(card).status == "cache"


def test_table_card_maps_to_heatmap_response() -> None:
    card = Card(
        id="heatmap-crypto",
        kind=CardKind.table,
        meta=None,
        state=SignalState.degraded,
        updated_at=5,
        payload=TablePayload(
            tiles=[
                HeatmapTile(
                    symbol="BTC",
                    name="Bitcoin",
                    change_percent=1.5,
                    price=1.0,
                    weight=2.0,
                )
            ]
        ),
    )
    legacy = to_heatmap_response(card)
    assert legacy.status == "cache"
    assert legacy.tiles[0].subtitle is None
    assert legacy.model_dump(by_alias=True)["tiles"][0]["symbol"] == "BTC"


def test_unsafe_urls_neutralized() -> None:
    item = CardItem(id="1", title="x", url="javascript:alert(1)")
    assert item.url == ""
