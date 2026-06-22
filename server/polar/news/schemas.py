"""Wire schemas for the public news endpoints.

Field names are camelCase on the wire (``mobileUrl``, ``pubDate``,
``updatedTime``) to match the frontend's item shape — these endpoints
power the public landing page where the item list is rendered verbatim.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class NewsExtra(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    hover: str | None = None
    info: str | None = None
    icon: str | None = None
    # Epoch ms or preformatted string — sources differ; the client only
    # feeds it to a relative-time formatter when numeric.
    date: int | str | None = None


class NewsItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    title: str
    url: str
    mobile_url: str | None = Field(default=None, alias="mobileUrl")
    pub_date: int | None = Field(default=None, alias="pubDate")  # epoch ms
    extra: NewsExtra | None = None


class SourceResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    # "success" = fetched (or fresh-enough) content; "cache" = stale-but-
    # within-TTL content served without refetching.
    status: Literal["success", "cache"]
    id: str
    updated_time: int = Field(alias="updatedTime")  # epoch ms
    items: list[NewsItem]


class SourceMeta(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    color: str
    column: str | None = None
    type: Literal["hottest", "realtime"] | None = None
    home: str | None = None
    title: str | None = None
    desc: str | None = None
    interval: int  # freshness window, ms
    redirect: str | None = None


class BatchRequest(BaseModel):
    sources: list[str] = Field(min_length=1, max_length=256)
