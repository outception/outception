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


class BriefingPublisher(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    source_id: str = Field(alias="sourceId")
    name: str
    logo: str | None = None


class BriefingItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    cluster_id: str = Field(alias="clusterId")
    title: str
    url: str
    mobile_url: str | None = Field(default=None, alias="mobileUrl")
    score: int | None = None
    category: str
    why: str | None = None
    publisher_count: int = Field(alias="publisherCount")
    publishers: list[BriefingPublisher] = Field(default_factory=list)
    pub_date: int | None = Field(default=None, alias="pubDate")
    # Both summaries take url plus sourceName, so the lead publisher travels.
    lead_source_name: str = Field(alias="leadSourceName")
    item: NewsItem


class BriefingPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    kind: Literal[CardKind.briefing] = CardKind.briefing
    profile: str
    built_at: int = Field(alias="builtAt")  # epoch ms
    stale_after_ms: int = Field(alias="staleAfterMs")
    items: list[BriefingItem]


class StripPayload(BaseModel):
    """A one-line attachment to another card. Today only weather, on the
    country and city cards."""

    model_config = ConfigDict(populate_by_name=True)

    kind: Literal[CardKind.strip] = CardKind.strip
    attached_to: str = Field(alias="attachedTo")
    weather: WeatherResponse | None = None


CardPayload = Annotated[
    FeedPayload | TablePayload | BriefingPayload | StripPayload,
    Field(discriminator="kind"),
]


class Card(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    kind: CardKind
    # Source cards carry their catalog entry; briefing and strip cards carry
    # none, which is why clients keep their own names for them.
    meta: SourceMeta | None = None
    state: SignalState
    updated_at: int = Field(alias="updatedAt")  # epoch ms
    payload: CardPayload
