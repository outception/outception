"""Wire schemas for the public news endpoints.

Field names are camelCase on the wire (``mobileUrl``, ``pubDate``,
``updatedTime``) to match the frontend's item shape — these endpoints
power the public landing page where the item list is rendered verbatim.
"""

from typing import Annotated, Literal
from urllib.parse import urlparse

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
)


def _safe_external_url(value: str | None) -> str | None:
    """Neutralize non-http(s) URLs coming from untrusted feeds so they can never
    become a ``javascript:``/``data:`` href when rendered in an ``<a>`` tag.
    Returns the URL unchanged when it's http(s), otherwise an empty string (the
    link goes nowhere instead of executing)."""
    if not value:
        return value
    try:
        scheme = urlparse(value).scheme.lower()
    except ValueError:
        return ""
    return value if scheme in ("http", "https") else ""


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

    @field_validator("url", "mobile_url")
    @classmethod
    def _neutralize_unsafe_urls(cls, value: str | None) -> str | None:
        return _safe_external_url(value)


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


class NewsSearchItem(BaseModel):
    """A headline matched by search, tagged with its source."""

    model_config = ConfigDict(populate_by_name=True)

    source_id: str = Field(alias="sourceId")
    source_name: str = Field(alias="sourceName")
    item: NewsItem


class NewsSearchResponse(BaseModel):
    """Search results: matching sources (by name) and matching cached
    headlines."""

    sources: list[SourceMeta]
    items: list[NewsSearchItem]


class FollowedSources(BaseModel):
    """The canonical ids of the sources the authenticated user follows."""

    source_ids: list[str] = Field(alias="sourceIds")

    model_config = ConfigDict(populate_by_name=True)


class WeatherCurrent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    temperature: float
    apparent_temperature: float = Field(alias="apparentTemperature")
    weather_code: int = Field(alias="weatherCode")  # WMO code; mapped client-side
    wind_speed: float = Field(alias="windSpeed")  # km/h
    humidity: int  # %
    is_day: bool = Field(alias="isDay")


class WeatherDaily(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    date: str  # ISO date (YYYY-MM-DD) in the location's timezone
    weather_code: int = Field(alias="weatherCode")
    temp_max: float = Field(alias="tempMax")
    temp_min: float = Field(alias="tempMin")


class TranslateRequest(BaseModel):
    """A batch of news headlines to machine-translate into one target language."""

    # Cap both the batch size AND each headline's length: without the per-item
    # bound a client could POST 256 multi-megabyte strings, each of which is
    # packed into an upstream GET query string.
    texts: list[Annotated[str, StringConstraints(max_length=512)]] = Field(
        min_length=1, max_length=256
    )
    target: str = Field(min_length=2, max_length=8)


class TranslateResponse(BaseModel):
    translations: list[str]


class WeatherResponse(BaseModel):
    """Current conditions and a short daily forecast for the weather card,
    proxied from Open-Meteo and localized to the reader's coordinates or IP
    country capital."""

    model_config = ConfigDict(populate_by_name=True)

    location: str
    latitude: float
    longitude: float
    timezone: str
    current: WeatherCurrent
    daily: list[WeatherDaily]
