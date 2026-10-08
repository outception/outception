from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, field_validator

from outception.models import LaunchStatus

Kicker = Literal["new", "update", "open source"]
NAME_CHARS = 60
TAGLINE_CHARS = 100
DESCRIPTION_CHARS = 300
SLOTS_PER_DAY = 5


def _https(value: HttpUrl) -> HttpUrl:
    if value.scheme != "https":
        raise ValueError("the link must use https")
    return value


class LaunchCreate(BaseModel):
    name: str = Field(min_length=2, max_length=NAME_CHARS)
    tagline: str = Field(min_length=2, max_length=TAGLINE_CHARS)
    url: HttpUrl
    logo_url: HttpUrl | None = None
    kicker: Kicker = "new"
    description: str = Field(default="", max_length=DESCRIPTION_CHARS)
    contact_email: EmailStr
    preferred_day: date | None = None

    _https_url = field_validator("url")(_https)

    @field_validator("logo_url")
    @classmethod
    def _https_logo(cls, value: HttpUrl | None) -> HttpUrl | None:
        return _https(value) if value is not None else None


class LaunchUpdate(BaseModel):
    """The submitter's own edit. A withdrawn or rejected product edited this
    way goes back into the queue."""

    name: str | None = Field(default=None, min_length=2, max_length=NAME_CHARS)
    tagline: str | None = Field(default=None, min_length=2, max_length=TAGLINE_CHARS)
    url: HttpUrl | None = None
    logo_url: HttpUrl | None = None
    kicker: Kicker | None = None
    description: str | None = Field(default=None, max_length=DESCRIPTION_CHARS)
    contact_email: EmailStr | None = None
    preferred_day: date | None = None

    @field_validator("url", "logo_url")
    @classmethod
    def _https_links(cls, value: HttpUrl | None) -> HttpUrl | None:
        return _https(value) if value is not None else None


class LaunchEdit(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=NAME_CHARS)
    tagline: str | None = Field(default=None, min_length=2, max_length=TAGLINE_CHARS)
    description: str | None = Field(default=None, max_length=DESCRIPTION_CHARS)
    kicker: Kicker | None = None


class LaunchApprove(BaseModel):
    day: date
    featured: bool = False


class LaunchReject(BaseModel):
    note: str = Field(default="", max_length=500)


class LaunchRead(BaseModel):
    """A product as the archive and the card see it: no contact email, no
    submitter."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    tagline: str
    url: str
    logo: str | None
    kicker: str
    description: str
    state: LaunchStatus
    featured: bool
    day: date | None
    position: int | None
    created_at: datetime


class LaunchMine(LaunchRead):
    """The submitter's own view adds the founder's note and the reach."""

    reviewer_note: str | None
    contact_email: str
    views: int = 0
    clicks: int = 0


class LaunchStatDay(BaseModel):
    day: date
    views: int
    clicks: int


class LaunchStats(BaseModel):
    """A product's reach: totals, then the last days newest first."""

    views: int
    clicks: int
    days: list[LaunchStatDay]


class LaunchViews(BaseModel):
    """The products the wall just showed; at most one card's worth."""

    ids: list[UUID] = Field(min_length=1, max_length=10)


class LaunchDay(BaseModel):
    day: date
    items: list[LaunchRead]


class LaunchArchive(BaseModel):
    days: list[LaunchDay]


class LaunchQueue(BaseModel):
    items: list[LaunchMine]
    slots: dict[str, int]  # day -> taken slots, for the date picker
