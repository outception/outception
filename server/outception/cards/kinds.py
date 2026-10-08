"""The kind registry: how a catalog entry's type maps to a card kind, and
how non-source cards are addressed."""

from enum import StrEnum


class CardKind(StrEnum):
    feed = "feed"
    table = "table"
    strip = "strip"  # type: ignore[assignment]  # the wire value shadows str.strip


# Non-source cards use reserved ids so they never collide with a source.
WEATHER_STRIP_ID = "weather"


def kind_for_type(source_type: str | None) -> CardKind:
    """`SourceMeta.type` decides the kind: `heatmap` is a table; `hottest`,
    `realtime` and unset are feeds. `game` has no rows and no kind."""
    if source_type == "heatmap":
        return CardKind.table
    if source_type == "game":
        raise ValueError("game sources are not cards")
    return CardKind.feed


def kind_for_id(card_id: str, source_type: str | None = None) -> CardKind:
    if card_id == WEATHER_STRIP_ID:
        return CardKind.strip
    return kind_for_type(source_type)
