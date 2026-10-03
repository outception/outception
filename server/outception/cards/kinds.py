"""The kind registry: how a catalog entry's type maps to a card kind, and
how non-source cards are addressed."""

from enum import StrEnum


class CardKind(StrEnum):
    feed = "feed"
    table = "table"
    briefing = "briefing"
    strip = "strip"  # type: ignore[assignment]  # the wire value shadows str.strip


# Non-source cards use namespaced ids so they never collide with a source.
BRIEFING_PREFIX = "briefing:"
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
    if card_id.startswith(BRIEFING_PREFIX):
        return CardKind.briefing
    if card_id == WEATHER_STRIP_ID:
        return CardKind.strip
    return kind_for_type(source_type)


def briefing_card_id(profile: str) -> str:
    return f"{BRIEFING_PREFIX}{profile}"


def briefing_profile(card_id: str) -> str | None:
    if not card_id.startswith(BRIEFING_PREFIX):
        return None
    return card_id[len(BRIEFING_PREFIX) :] or None
