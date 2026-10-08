# mypy: ignore-errors
"""Capture the live tree's parity fixtures. Runs ONLY in the external venv of
the live package, with cwd at the live server directory (reads .env.testing).
Writes nothing into the live tree; output goes to the directory in argv[1]."""

import asyncio
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

os.environ["PYTHONTZPATH"] = ""

from fastapi import Response
from outception.news.templates import resolve_templates

from outception.news import metadata
from outception.news.endpoints import (
    _COLUMN_ORDER,
    _SOURCES_BODY,
    _SOURCES_ETAG,
    _SOURCES_PAYLOAD,
    default_cards,
)
from outception.news.heatmap import HEATMAPS
from outception.news.registry import DISABLED_SOURCES
from outception.news.search import _SOURCE_INDEX

OUT = Path(sys.argv[1])
LIVE = Path.cwd().parent
GAME_IDS = ("crossword", "sudoku", "solitaire", "cube")
COUNTRIES = [
    "US",
    "GB",
    "IE",
    "CA",
    "AU",
    "NZ",
    "IN",
    "NG",
    "ZA",
    "SG",
    "PH",
    "DE",
    "FR",
    "ES",
    "IT",
    "NL",
    "SE",
    "NO",
    "PL",
    "PT",
    "CH",
    "AT",
    "BE",
    "BR",
    "MX",
    "AR",
    "JP",
    "KR",
    "ID",
    "TR",
]


def dump(name: str, obj: object) -> None:
    (OUT / name).write_text(
        json.dumps(obj, indent=1, ensure_ascii=False, sort_keys=False) + "\n"
    )


async def main() -> None:
    head = subprocess.check_output(
        ["git", "-C", str(LIVE), "rev-parse", "HEAD"], text=True
    ).strip()

    decks: dict[str, list[str]] = {}
    decks_raw: dict[str, list[str]] = {}
    for cc in [None, *COUNTRIES]:
        key = cc or ""
        raw = await default_cards(Response(), country=cc, cf_ipcountry=None)
        decks_raw[key] = raw
        decks[key] = [sid for sid in raw if sid not in GAME_IDS]
    dump("default_cards.json", decks)
    dump(
        "templates.json", {cc or "": resolve_templates(cc) for cc in [None, *COUNTRIES]}
    )

    (OUT / "sources_body.json").write_bytes(_SOURCES_BODY)
    assert hashlib.md5(_SOURCES_BODY).hexdigest()[:20] == _SOURCES_ETAG.strip('"')
    gated = {
        hid: spec.provider
        for hid, spec in HEATMAPS.items()
        if spec.provider in ("finnhub", "cricket")
    }
    dump(
        "registry.json",
        {
            "live_head": head,
            "etag": _SOURCES_ETAG,
            "etag_rule": "md5(sources_body bytes).hexdigest()[:20], quoted",
            "serialization": {
                "model": "SourceMeta",
                "model_dump": {"by_alias": True, "exclude_none": True},
                "json_dumps": {"ensure_ascii": False, "separators": [",", ":"]},
                "fields": [
                    "id",
                    "interval",
                    "name",
                    "color",
                    "column",
                    "type",
                    "home",
                    "title",
                    "desc",
                    "redirect",
                    "logo",
                ],
            },
            "order": "SOURCES registration order, stable-sorted by column rank; disabled ids excluded",
            "column_order": _COLUMN_ORDER,
            "captured_with_keys": ["FINNHUB_API_KEY", "CRICKETDATA_API_KEY"],
            "key_gated_heatmaps": gated,
            "counts": {
                "sources_total": len(metadata.SOURCES),
                "disabled": len(DISABLED_SOURCES),
                "served_rows": len(_SOURCES_PAYLOAD),
                "heatmaps_total": len(HEATMAPS),
            },
            "served_ids": [m.id for m in _SOURCES_PAYLOAD],
            "disabled_ids": sorted(DISABLED_SOURCES),
            "game_ids_stripped": list(GAME_IDS),
            "game_ids_present_in_live": [g for g in GAME_IDS if g in metadata.SOURCES],
            "decks_raw_lengths": {k: len(v) for k, v in decks_raw.items()},
        },
    )
    dump(
        "search_index.json",
        [
            {
                "id": sid,
                "blob": blob,
                "meta": meta.model_dump(by_alias=True, exclude_none=True),
            }
            for sid, blob, meta in _SOURCE_INDEX
        ],
    )
    print(
        "decks",
        len(decks),
        "templates countries",
        len(COUNTRIES) + 1,
        "rows",
        len(_SOURCES_PAYLOAD),
        "etag",
        _SOURCES_ETAG,
    )


asyncio.run(main())
