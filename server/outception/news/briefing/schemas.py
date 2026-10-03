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
    profiles: list[BriefingProfile]


class BriefingMine(BaseModel):
    profiles: list[str]
