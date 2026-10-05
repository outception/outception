from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from outception.cards.schemas import BriefingItem


class BriefingResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: Literal["success", "cache"]
    profile: str
    built_at: int = Field(alias="builtAt")  # epoch ms
    stale_after_ms: int = Field(alias="staleAfterMs")
    items: list[BriefingItem]


class BriefingDay(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    built_for: date = Field(alias="builtFor")
    built_at: int = Field(alias="builtAt")
    items: list[BriefingItem]


class BriefingHistoryResponse(BaseModel):
    profile: str
    days: list[BriefingDay]


class BriefingProfile(BaseModel):
    id: str
    template: str
    categories: list[str]


class BriefingProfilesResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    profiles: list[BriefingProfile]
    # The key a browser subscribes with; null while web push is off.
    push_public_key: str | None = Field(default=None, alias="pushPublicKey")


class PushKeys(BaseModel):
    p256dh: str = Field(min_length=16, max_length=512)
    auth: str = Field(min_length=8, max_length=128)


class PushSubscribe(BaseModel):
    """One device asking for the morning briefing. `endpoint` is the push
    service URL on the web and the device token in the app."""

    kind: Literal["web", "app"]
    endpoint: str = Field(min_length=8, max_length=2048)
    keys: PushKeys | None = None


class PushUnsubscribe(BaseModel):
    endpoint: str = Field(min_length=8, max_length=2048)


class BriefingMine(BaseModel):
    profiles: list[str]
