"""Wire schemas for the Promoted card.

One clearly-labeled sponsored card in the news cards. Slots are provisioned
by an operator (scripts/promoted.py) when a Push package is sold on
outception.ai - there is no self-serve purchase flow. Field names are
camelCase on the wire to match the frontend's item shape, like the news
schemas.
"""

from datetime import datetime
from typing import Annotated
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator


def _http_only(value: str | None) -> str | None:
    """Only ever hand the client an http(s) URL - a promoted slot is operator
    data today, but the card renders it in an href/src, so neutralize anything
    else just like news item links."""
    if not value:
        return value
    try:
        scheme = urlparse(value).scheme.lower()
    except ValueError:
        return ""
    return value if scheme in ("http", "https") else ""


class PromotedSlot(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    business_name: Annotated[str, StringConstraints(max_length=120)] = Field(
        alias="businessName"
    )
    video_url: str = Field(alias="videoUrl")
    click_url: str | None = Field(default=None, alias="clickUrl")
    tagline: Annotated[str, StringConstraints(max_length=200)] | None = None
    ends_at: datetime = Field(alias="endsAt")

    @field_validator("video_url", "click_url")
    @classmethod
    def _neutralize_urls(cls, v: str | None) -> str | None:
        return _http_only(v)


class QueuedPromotion(BaseModel):
    """A paid, waiting run: the slot fields plus how long it holds the card
    once it advances. Stored as JSON in the Redis FIFO queue.

    Mirrors PromotedSlot's constraints exactly: a limit enforced only at
    activation rejects the entry AFTER it was paid for and popped - the
    public endpoint 500s and the run is lost. Bad input must die at
    enqueue, in the operator's face."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    business_name: Annotated[str, StringConstraints(max_length=120)] = Field(
        alias="businessName"
    )
    video_url: str = Field(alias="videoUrl")
    click_url: str | None = Field(default=None, alias="clickUrl")
    tagline: Annotated[str, StringConstraints(max_length=200)] | None = None
    duration_seconds: Annotated[int, Field(gt=0, alias="durationSeconds")]

    @field_validator("video_url", "click_url")
    @classmethod
    def _neutralize_urls(cls, v: str | None) -> str | None:
        return _http_only(v)
