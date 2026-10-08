"""The legacy views, built from the envelope by one mapper so the two can
never drift. `status` is `success` when the state is `nominal`, else
`cache`; `updatedTime` is `updatedAt`; the envelope-only fields are dropped.
Failures stay HTTP 502 and never reach these mappers."""

from typing import Literal

from outception.net.state import SignalState
from outception.news.schemas import HeatmapResponse, NewsItem, SourceResponse

from .schemas import Card, FeedPayload, TablePayload

LegacyStatus = Literal["success", "cache"]


def legacy_status(state: SignalState) -> LegacyStatus:
    return "success" if state == SignalState.nominal else "cache"


def to_source_response(card: Card) -> SourceResponse:
    if not isinstance(card.payload, FeedPayload):
        raise ValueError(f"card {card.id} is not a feed card")
    items = [
        NewsItem.model_validate(
            item.model_dump(by_alias=True, exclude={"cluster_id", "publisher_count"})
        )
        for item in card.payload.items
    ]
    return SourceResponse(
        status=legacy_status(card.state),
        id=card.id,
        updated_time=card.updated_at,
        items=items,
    )


def to_heatmap_response(card: Card) -> HeatmapResponse:
    if not isinstance(card.payload, TablePayload):
        raise ValueError(f"card {card.id} is not a table card")
    return HeatmapResponse(
        status=legacy_status(card.state),
        id=card.id,
        updated_time=card.updated_at,
        tiles=list(card.payload.tiles),
    )
