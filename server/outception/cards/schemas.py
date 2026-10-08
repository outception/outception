"""The card envelope: `{id, kind, meta, state, updatedAt, payload}`.

Kinds are additive; the envelope never changes shape. Fields that only the
envelope carries (`clusterId`, `publisherCount`, `state`) never appear on
the legacy responses, which `cards.views` builds from the same objects.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from outception.net.state import SignalState
from outception.news.schemas import HeatmapTile, NewsItem, SourceMeta, WeatherResponse

from .kinds import CardKind


class CardItem(NewsItem):
    """A feed item on the envelope: the legacy item plus what clustering
    adds. Both extras are optional so an unclustered item serializes exactly
    like a legacy one apart from the two nulls."""

    cluster_id: str | None = Field(default=None, alias="clusterId")
    publisher_count: int | None = Field(default=None, alias="publisherCount")


class FeedPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    kind: Literal[CardKind.feed] = CardKind.feed
    items: list[CardItem]


class TablePayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    kind: Literal[CardKind.table] = CardKind.table
    tiles: list[HeatmapTile]


class StripPayload(BaseModel):
    """A one-line attachment to another card. Today only weather, on the
    country and city cards."""

    model_config = ConfigDict(populate_by_name=True)

    kind: Literal[CardKind.strip] = CardKind.strip
    attached_to: str = Field(alias="attachedTo")
    weather: WeatherResponse | None = None


CardPayload = Annotated[
    FeedPayload | TablePayload | StripPayload,
    Field(discriminator="kind"),
]


class Card(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    kind: CardKind
    # Source cards carry their catalog entry; strip cards carry none, which
    # is why clients keep their own names for them.
    meta: SourceMeta | None = None
    state: SignalState
    updated_at: int = Field(alias="updatedAt")  # epoch ms
    payload: CardPayload
