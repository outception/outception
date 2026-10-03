"""Schemas of the catalog data files under `news/data/`. One file per
family; each under a few thousand lines; all JSON.

The source rows reproduce the live registry exactly (same ids, same fields,
same order), which a snapshot test asserts against the parity fixtures.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Column = Literal[
    "news",
    "world",
    "sports",
    "finance",
    "science",
    "entertainment",
    "tech",
    "social",
    "betting",
]

# Default card set order: lead with mainstream and global news and sports the
# way a front page does, and push tech, social and niche columns lower.
# Sources keep their registration order within a column (stable sort).
COLUMN_ORDER: dict[str, int] = {
    "news": 0,
    "world": 1,
    "sports": 2,
    "finance": 3,
    "science": 4,
    "entertainment": 5,
    "tech": 6,
    "social": 7,
    "betting": 8,
}


class SourceRow(BaseModel):
    """One source as the registry serves it. `adapter` names the fetcher
    family (`rss`, `gnews`, `youtube`, ...) and `config` its arguments;
    both stay server-side."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    color: str
    column: Column | None = None
    type: Literal["hottest", "realtime", "heatmap", "game"] | None = None
    home: str | None = None
    title: str | None = None
    desc: str | None = None
    interval: int | None = None  # ms; the registry default when unset
    redirect: str | None = None
    logo: str | None = None
    adapter: str | None = None
    config: dict[str, object] = Field(default_factory=dict)


class DisabledRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    reason: str
    since: str  # ISO date of the audit that disabled it


class TemplateRow(BaseModel):
    """A Starter: a static roster plus `extras`, references to the country
    tables (`country:<table>`) resolved per request. A Starter is also a
    briefing profile id."""

    model_config = ConfigDict(extra="forbid")

    id: str
    sources: list[str]
    extras: list[str] = Field(default_factory=list)
    profile: str | None = None


class LiveSignalRow(BaseModel):
    """A live-signal table: a keyless upstream polled by the worker. Off by
    default; switched on by data, not by a setting."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    provider: str
    interval: int  # ms
    fresh_for: int
    stale_for: int
    budget_per_day: int | None = None
    cooldown_range: tuple[int, int] = (30, 900)
    byte_cap: int = 2 * 1024 * 1024
    terms: str | None = None
    enabled: bool = False
    countries: list[str] | None = None
    season: tuple[int, int] | None = None
    cities: list[str] | None = None


class CreditRow(BaseModel):
    """One line of the credits drawer and `DATA_SOURCES.md`: who the data
    comes from and under what terms."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    url: str
    terms: str
    used_for: str


class DeckEntryRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    inject_after: list[str] = Field(default_factory=list)
    swap: str | None = None
    enabled: bool = True
    season: tuple[int, int] | None = None
    countries: list[str] | None = None


class DeckFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base: list[DeckEntryRow]
    briefing_profile_by_country: dict[str, str] = Field(default_factory=dict)
    default_briefing_profile: str = "news-junkie"


class CountryTablesFile(BaseModel):
    """`country/<table>.json`: country code to ids."""

    model_config = ConfigDict(extra="forbid")

    table: str
    entries: dict[str, list[str]]
