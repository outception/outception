# Parity fixtures from the live tree

Captured on 2026-10-03 from the live product at
`/home/admin1/Desktop/outception`, HEAD `b176b6f1db7d20f95c4cccd357d2f6b98993d396`,
working tree clean before and after. Nothing was written into the live tree:
the capture ran in an external venv (`UV_PROJECT_ENVIRONMENT=<scratchpad>/l-venv
uv sync --project <live>/server --frozen`) with `PYTHONDONTWRITEBYTECODE=1`.

These files are the M2 parity gate (PLATFORM_PLAN.md section 3.1): the rebuilt
deck composer, Starters, catalog loader and OpenAPI must reproduce them.

| File | What | Consumer |
| --- | --- | --- |
| `default_cards.json` | `GET /v1/news/default-cards` for each country key, plus `""` for an unknown visitor. The four game ids (`crossword`, `sudoku`, `solitaire`, `cube`) are stripped by decision; the synthetic `weather` id stays last. | `cards/deck.py` and `news-core/deck.ts` parity test |
| `templates.json` | `GET /v1/news/templates` for the same countries: every Starter with its resolved source ids. | Starters parity test |
| `sources_body.json` | The exact bytes of `GET /v1/news/sources` as served (pre-serialized, compact, UTF-8). | catalog snapshot-equality test |
| `registry.json` | The ETag inputs: the ETag, the hashing rule, serialization settings, column order, served ids in order, disabled ids, the key-gated table ids and the keyless ETag. | catalog loader test, `/sources` ETag test |
| `search_index.json` | The five-field subset the source search serves per hit, in index order. | search parity test |
| `openapi.json` | The live OpenAPI document with accounts enabled (the surface the swap ships). | additive-diff gate |
| `openapi.accounts-off.json` | The same document as production mounts it today (`ACCOUNTS_ENABLED=false`): news and promoted only. | additive-diff gate for the store binary |
| `capture_live.py` | The script that produced the deck, Starter, registry and search files. It runs only inside the external live venv, never in this package. | re-capture if ever needed |

## How it was run

```bash
cd /home/admin1/Desktop/outception/server
PYTHONPATH=$PWD PYTHONDONTWRITEBYTECODE=1 OUTCEPTION_ENV=testing \
  OUTCEPTION_FINNHUB_API_KEY=parity OUTCEPTION_CRICKETDATA_API_KEY=parity \
  <scratchpad>/l-venv/bin/python capture_live.py <this directory>
# OpenAPI, same env, with and without OUTCEPTION_ACCOUNTS_ENABLED=false:
PYTHONTZPATH="" ... python -m scripts.generate_openapi
```

`OUTCEPTION_ENV=testing` reads the tracked `.env.testing`, which holds no
secrets. The two table keys were set to a placeholder so the key-gated
table rows (six stock tables and the cricket table) are present, as they are
when the keys are configured. The keyless ETag and row count are recorded in
`registry.json` under `keyless` for the other configuration. The game route
`/v1/news/crossword` is in both OpenAPI documents because it is live today;
its removal is a decided, non-additive change the diff gate must allow by name.

## The thirty countries

No visitor analytics exist in either tree, so the list is the thirty
countries with the widest country-table coverage, which also covers every
country named in the verification list of PLATFORM_PLAN.md section 10:

US, GB, IE, CA, AU, NZ, IN, NG, ZA, SG, PH, DE, FR, ES, IT, NL, SE, NO, PL,
PT, CH, AT, BE, BR, MX, AR, JP, KR, ID, TR, plus the unknown-country case.

Change the list in `capture_live.py` and re-run if the founder supplies a
real ranking; the live tree does not change before the swap, so a re-capture
gives the same answers for any country.
