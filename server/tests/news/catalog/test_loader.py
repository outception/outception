import json
from pathlib import Path

import pytest

from outception.news.catalog import CatalogError, load_catalog


def _write(data_dir: Path, name: str, payload: object) -> None:
    path = data_dir / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))


def test_empty_catalog_loads(tmp_path: Path) -> None:
    catalog = load_catalog(tmp_path)
    assert catalog.sources == ()
    assert catalog.deck.base == []
    assert catalog.ordered() == []


def test_shipped_data_files_load() -> None:
    catalog = load_catalog()
    assert catalog.deck.base


def test_order_is_column_rank_then_registration(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "sources.json",
        [
            {
                "id": "tech-a",
                "name": "A",
                "color": "#000",
                "column": "tech",
                "adapter": "rss",
            },
            {
                "id": "news-b",
                "name": "B",
                "color": "#000",
                "column": "news",
                "adapter": "rss",
            },
            {
                "id": "news-c",
                "name": "C",
                "color": "#000",
                "column": "news",
                "adapter": "rss",
            },
            {
                "id": "off",
                "name": "Off",
                "color": "#000",
                "column": "news",
                "adapter": "rss",
            },
        ],
    )
    _write(
        tmp_path,
        "disabled.json",
        [{"id": "off", "reason": "dead feed", "since": "2026-10-01"}],
    )
    catalog = load_catalog(tmp_path)
    assert [row.id for row in catalog.ordered()] == ["news-b", "news-c", "tech-a"]
    assert catalog.is_disabled("off")
    assert catalog.is_known("off")


@pytest.mark.parametrize(
    ("files", "message"),
    [
        (
            {
                "sources.json": [
                    {"id": "a", "name": "A", "color": "#000", "adapter": "rss"},
                    {"id": "a", "name": "A", "color": "#000", "adapter": "rss"},
                ]
            },
            "duplicate source id",
        ),
        (
            {
                "sources.json": [
                    {"id": "a", "name": "A", "color": "#000", "redirect": "zzz"}
                ]
            },
            "redirect to unknown",
        ),
        ({"sources.json": [{"id": "a", "name": "A", "color": "#000"}]}, "no adapter"),
        (
            {"templates.json": [{"id": "developer", "sources": ["ghost"]}]},
            "names unknown id",
        ),
        (
            {
                "templates.json": [
                    {"id": "developer", "sources": [], "extras": ["country:sports"]}
                ]
            },
            "unknown country table",
        ),
        (
            {"decks/default.json": {"base": [{"id": "ghost"}]}},
            "names unknown id",
        ),
        (
            {
                "sources.json": [
                    {
                        "id": "a",
                        "name": "A",
                        "color": "#000",
                        "adapter": "rss",
                        "bogus": 1,
                    }
                ]
            },
            "sources.json",
        ),
    ],
)
def test_broken_catalog_fails(
    tmp_path: Path, files: dict[str, object], message: str
) -> None:
    for name, payload in files.items():
        _write(tmp_path, name, payload)
    with pytest.raises(CatalogError, match=message):
        load_catalog(tmp_path)


def test_country_tables_resolve(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "sources.json",
        [
            {"id": "sport-hurling", "name": "H", "color": "#000", "adapter": "rss"},
            {"id": "bbcsport", "name": "S", "color": "#000", "adapter": "rss"},
        ],
    )
    _write(
        tmp_path,
        "country/sports.json",
        {"table": "sports", "entries": {"ie": ["sport-hurling"]}},
    )
    _write(
        tmp_path,
        "templates.json",
        [{"id": "sports-fan", "sources": ["bbcsport"], "extras": ["country:sports"]}],
    )
    _write(
        tmp_path,
        "decks/default.json",
        {"base": [{"id": "bbcsport", "swap": "sports"}]},
    )
    catalog = load_catalog(tmp_path)
    assert catalog.country_tables == {"IE": {"sports": ("sport-hurling",)}}
