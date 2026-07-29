"""Wire schemas for the public news endpoints.

Field names are camelCase on the wire (``mobileUrl``, ``pubDate``,
``updatedTime``) to match the frontend's item shape - these endpoints
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
    # Epoch ms or preformatted string - sources differ; the client only
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
    # The publisher's own standfirst from the feed. Never serialized (cards
    # stay small); kept per URL in Redis by the cache writer so a tap on an
    # article we cannot summarize can still show the publisher's teaser.
    teaser: str | None = Field(default=None, exclude=True)

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
    # True while some headlines are still being translated into the requested
    # language (they are returned in the original for now): poll again soon.
    translations_pending: bool = Field(False, alias="translationsPending")


class SourceMeta(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    color: str
    column: str | None = None
    # "heatmap" sources carry no headlines: clients render their tiles from
    # /news/heatmap/{id} (see HeatmapResponse) instead of /news/{id}.
    type: Literal["hottest", "realtime", "heatmap", "game"] | None = None
    home: str | None = None
    title: str | None = None
    desc: str | None = None
    interval: int  # freshness window, ms
    redirect: str | None = None
    # Real logo/crest image URL for entity search-feeds (teams, brands, cities,
    # …); absent for feeds that fall back to a monogram or a shared icon.
    logo: str | None = None


class HeatmapTile(BaseModel):
    """One treemap tile: area from ``weight`` (market cap), color from
    ``changePercent``."""

    model_config = ConfigDict(populate_by_name=True)

    symbol: str
    name: str
    change_percent: float = Field(alias="changePercent")
    price: float
    weight: float
    # Display line under the symbol ("45 pts", "12-4"). When absent the client
    # formats changePercent as a signed percentage - market-style tiles.
    label: str | None = None
    # Where a tapped tile leads (quote page, store page, …). Server-supplied so
    # new heatmap kinds ship without client changes.
    url: str | None = None
    # Small brand mark rendered above the symbol on large-enough tiles
    # (company logo, coin icon, currency flag). Optional per tile.
    logo: str | None = None

    @field_validator("url")
    @classmethod
    def _neutralize_unsafe_urls(cls, value: str | None) -> str | None:
        return _safe_external_url(value)


class HeatmapResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    # Same semantics as SourceResponse: "success" = fresh, "cache" = stale-but-
    # served (upstream failed or rate-limited).
    status: Literal["success", "cache"]
    id: str
    updated_time: int = Field(alias="updatedTime")  # epoch ms
    tiles: list[HeatmapTile]


class NewsTemplate(BaseModel):
    """A starter template: a persona's curated source bundle, country-resolved.
    Display name/blurb live client-side, keyed by ``id``."""

    id: str
    sources: list[str]


class TemplatesResponse(BaseModel):
    templates: list[NewsTemplate]


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


class CrosswordClue(BaseModel):
    num: int
    clue: str
    row: int
    col: int
    len: int


class SummaryAvailability(BaseModel):
    """Whether a headline tap can expect an AI summary, decided from what the
    server already knows - so the client either opens the summary panel or
    sends the reader straight to the article, never both in a row."""

    available: bool = Field(
        description="False when the summary is known to be unavailable"
    )


class SummaryResponse(BaseModel):
    """AI summary for a headline tap: the model-written text plus the
    article URL it covers (the client links to it under the summary)."""

    summary: str = Field(description="Model-written summary of the article")
    url: str = Field(description="The article URL the summary covers")
    kind: Literal["summary", "teaser"] = Field(
        "summary",
        description=(
            "'summary' is model-written from the article; 'teaser' is the "
            "publisher's own standfirst, shown when the article itself is not "
            "available (paywall, bot wall)"
        ),
    )


class CrosswordResponse(BaseModel):
    """The daily syndicated crossword, parsed for the wall's puzzle card:
    the solution grid (# = block) plus numbered across/down clues."""

    id: str
    title: str
    author: str
    rows: int
    cols: int
    grid: list[str]
    across: list[CrosswordClue]
    down: list[CrosswordClue]


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
