"""The catalog reproduces the live registry: same ids, same fields, same
order, same bytes, same ETag; the Starters and the default deck resolve to
the live tree's answers for the thirty countries."""

import hashlib
import json
from pathlib import Path

import pytest

from outception.config import settings
from outception.news.catalog import load_catalog
from outception.news.catalog.decks import default_cards, resolve_templates
from outception.news.catalog.registry import Registry

PARITY = Path(__file__).resolve().parents[1] / "fixtures" / "parity"


@pytest.fixture(scope="module")
def registry() -> Registry:
    return Registry(load_catalog())


@pytest.fixture(autouse=True)
def keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "FINNHUB_API_KEY", "parity")
    monkeypatch.setattr(settings, "CRICKETDATA_API_KEY", "parity")


GAME_IDS = {"crossword", "sudoku", "solitaire", "cube"}
# The one addition decided by the plan: the Products of the day card, a
# normal source in the roster, the default deck and three Starters. The
# live snapshot predates it, so it is set aside before every comparison.
ADDED_IDS = {"products-of-the-day"}


def _live_rows() -> list[dict[str, object]]:
    """The live body minus the four game rows, removed by decision; that is
    the one difference the registry is allowed to have."""
    rows = json.loads((PARITY / "sources_body.json").read_bytes())
    return [row for row in rows if row["id"] not in GAME_IDS]


def test_sources_body_matches_the_live_tree(registry: Registry) -> None:
    expected = json.loads((PARITY / "registry.json").read_text())
    served = [row for row in json.loads(registry.body) if row["id"] not in ADDED_IDS]
    assert served == _live_rows()
    assert [m.id for m in registry.payload if m.id not in ADDED_IDS] == [
        sid for sid in expected["served_ids"] if sid not in GAME_IDS
    ]
    assert registry.etag == f'"{hashlib.md5(registry.body).hexdigest()[:20]}"'
    # the serialization settings are the live ones: compact, UTF-8 verbatim
    assert (
        json.dumps(served, ensure_ascii=False, separators=(",", ":")).encode()
        == json.dumps(_live_rows(), ensure_ascii=False, separators=(",", ":")).encode()
    )


def test_keyless_roster_drops_the_gated_tables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "FINNHUB_API_KEY", None)
    monkeypatch.setattr(settings, "CRICKETDATA_API_KEY", None)
    expected = json.loads((PARITY / "registry.json").read_text())
    keyless = Registry(load_catalog())
    gated = set(expected["key_gated_heatmaps"])
    assert len(keyless.payload) == expected["keyless"]["served_rows"] - len(
        GAME_IDS
    ) + len(ADDED_IDS)
    assert not gated & {m.id for m in keyless.payload}


def test_search_index(registry: Registry) -> None:
    expected = [
        row
        for row in json.loads((PARITY / "search_index.json").read_text())
        if row["id"] not in GAME_IDS
    ]
    actual = [
        {
            "id": sid,
            "blob": blob,
            "meta": meta.model_dump(by_alias=True, exclude_none=True),
        }
        for sid, blob, meta in registry.search_index
        if sid not in ADDED_IDS
    ]
    assert actual == expected


def test_default_decks_match_the_live_tree(registry: Registry) -> None:
    expected = json.loads((PARITY / "default_cards.json").read_text())
    for country, deck in expected.items():
        composed = default_cards(registry, country or None, month=10)
        assert [card for card in composed if card not in ADDED_IDS] == deck, (
            country or "unknown"
        )


def test_starters_match_the_live_tree(registry: Registry) -> None:
    expected = json.loads((PARITY / "templates.json").read_text())
    for country, templates in expected.items():
        resolved = [
            {
                **template,
                "sources": [s for s in template["sources"] if s not in ADDED_IDS],
            }
            for template in resolve_templates(registry, country or None)
        ]
        assert resolved == templates, country or "unknown"
