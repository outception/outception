"""Profiles as data: `news/data/profiles/<id>/` holds the routing rule,
the rubric with its levels, the why-line guidance and the category list.
The loader validates every reference; a broken profile fails the build."""

import json
import re
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ..catalog import catalog
from ..catalog import registry as catalog_registry

PROFILES_DIR = Path(__file__).resolve().parent.parent / "data" / "profiles"
LESSONS_MAX_LINES = 200
_FRONT_MATTER = re.compile(r"\A---\n(.*?)\n---\n?", re.DOTALL)


class ProfileError(ValueError):
    pass


class CategoryRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    max: int = Field(ge=1)
    criteria: str = Field(min_length=3)


class ProfileFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    template: str
    min_score: int = Field(default=6, ge=0, le=10)
    max_items: int = Field(default=30, ge=1)
    categories: list[CategoryRow]
    extra_sources: list[str] = Field(default_factory=list)
    exclude_sources: list[str] = Field(default_factory=list)


@dataclass(frozen=True)
class Profile:
    id: str
    template: str
    min_score: int
    max_items: int
    categories: tuple[CategoryRow, ...]
    sources: frozenset[str]  # the Starter's roster plus extras, minus excludes
    match_criteria: str
    match: str
    levels: dict[str, str]  # "0".."10" -> one line each
    rubric: str
    why: str
    lessons: str | None = None
    version: int = 1
    extra: dict[str, str] = field(default_factory=dict)

    @property
    def category_ids(self) -> tuple[str, ...]:
        return tuple(category.id for category in self.categories)


def _split_front_matter(text: str) -> tuple[dict[str, object], str]:
    match = _FRONT_MATTER.match(text)
    if match is None:
        return {}, text.strip()
    meta: dict[str, object] = {}
    current: str | None = None
    for line in match.group(1).splitlines():
        if not line.strip():
            continue
        if line.startswith("  ") and current is not None:
            key, _, value = line.strip().partition(":")
            nested = meta.setdefault(current, {})
            if isinstance(nested, dict):
                nested[key.strip().strip('"')] = value.strip().strip('"')
            continue
        key, _, value = line.partition(":")
        current = key.strip()
        meta[current] = value.strip().strip('"') if value.strip() else {}
    return meta, text[match.end() :].strip()


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as e:
        raise ProfileError(f"{path}: {e}") from e


def load_profile(directory: Path) -> Profile:
    try:
        spec = ProfileFile.model_validate(json.loads(_read(directory / "profile.json")))
    except (ValueError, ValidationError) as e:
        raise ProfileError(f"{directory.name}/profile.json: {e}") from e
    if spec.id != directory.name:
        raise ProfileError(
            f"{directory.name}: profile id {spec.id!r} does not match its folder"
        )
    match_meta, match_body = _split_front_matter(_read(directory / "match.md"))
    score_meta, rubric = _split_front_matter(_read(directory / "score.md"))
    levels_raw = score_meta.get("levels")
    if not isinstance(levels_raw, dict) or set(levels_raw) != {
        str(i) for i in range(11)
    }:
        raise ProfileError(f"{spec.id}: score.md must name every level 0 to 10")
    levels = {str(i): str(levels_raw[str(i)]) for i in range(11)}
    criteria = str(match_meta.get("criteria") or "")
    if not criteria:
        raise ProfileError(f"{spec.id}: match.md has no criteria line")
    why = _read(directory / "why.md").strip()
    lessons_path = directory / "lessons.md"
    lessons: str | None = None
    if lessons_path.exists():
        lines = _read(lessons_path).splitlines()
        if len(lines) > LESSONS_MAX_LINES:
            raise ProfileError(
                f"{spec.id}: lessons.md is over {LESSONS_MAX_LINES} lines"
            )
        lessons = "\n".join(lines)
    ids = [category.id for category in spec.categories]
    if len(set(ids)) != len(ids):
        raise ProfileError(f"{spec.id}: duplicate category ids")
    if sum(category.max for category in spec.categories) > spec.max_items:
        raise ProfileError(f"{spec.id}: category maxima exceed max_items")
    data = catalog()
    template = next((t for t in data.templates if t.id == spec.template), None)
    if template is None:
        raise ProfileError(f"{spec.id}: unknown Starter {spec.template!r}")
    registry = catalog_registry()
    sources: set[str] = set()
    for source_id in [*template.sources, *spec.extra_sources]:
        resolved = registry.resolve_known(source_id)
        if resolved is None and source_id not in data.by_id:
            raise ProfileError(f"{spec.id}: unknown source {source_id!r}")
        sources.add(resolved or source_id)
    for source_id in spec.exclude_sources:
        if source_id not in data.by_id:
            raise ProfileError(f"{spec.id}: unknown excluded source {source_id!r}")
        sources.discard(source_id)
    return Profile(
        id=spec.id,
        template=spec.template,
        min_score=spec.min_score,
        max_items=spec.max_items,
        categories=tuple(spec.categories),
        sources=frozenset(sources),
        match_criteria=criteria,
        match=match_body,
        levels=levels,
        rubric=rubric,
        why=why,
        lessons=lessons,
        version=int(str(score_meta.get("version") or 1)),
    )


def load_profiles(directory: Path = PROFILES_DIR) -> dict[str, Profile]:
    profiles: dict[str, Profile] = {}
    if not directory.exists():
        return profiles
    for child in sorted(directory.iterdir()):
        if child.is_dir() and (child / "profile.json").exists():
            profile = load_profile(child)
            profiles[profile.id] = profile
    return profiles


@cache
def profiles() -> dict[str, Profile]:
    return load_profiles()


def enabled_profile_ids() -> list[str]:
    from outception.config import settings

    allowed = settings.BRIEFING_PROFILES
    return [pid for pid in profiles() if not allowed or pid in allowed]
