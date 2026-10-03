# Catalog data

Every declared thing the wall can show lives here as JSON, one file per
family, validated by `news/catalog/loader.py` at startup:

- `sources.json`: the source rows the registry serves, in registration order
- `disabled.json`: ids retired by an audit, with the date and reason
- `templates.json`: the Starters, rosters plus country-table references
- `live_signals.json`: the live-signal tables, off until switched on here
- `credits.json`: the credits drawer and the generated data sources list
- `decks/default.json`: the default deck's ordered base list and its rules
- `country/*.json`: the country tables (sports, sport tables, top city,
  property, business, deals, events, health, travel, podcast, education)

The files are empty until the news domain is ported from the live product;
the parity fixtures under `tests/news/fixtures/parity` are what the filled
catalog must reproduce.
