# Outception

A live news deck where your feed is your choice. Pick the sources and topics you
care about and read the news for free.

## What it is

An open, no-login **live news deck**: a continuously updated feed of headlines
from 10,000+ sources (Hacker News, The Verge, TechCrunch, Ars Technica, BBC News,
CNN, The Guardian, NPR, GitHub, Product Hunt, Steam, ESPN, and more), laid out
in topic columns (news, world, sports, finance, science, entertainment, tech,
social, betting) alongside live **heatmap table cards**: stock sectors, crypto,
and league tables for 20+ competitions with real qualification-zone colors.

It's free to read. The web deck lives at [outception.com](https://outception.com);
the iOS app is on the [App Store](https://apps.apple.com/app/id6793827093).

## Features

- News deck on web and mobile, laid out by topic
- Follow, filter, and search across 10,000+ sources; no account required to read
- Live heatmap tables: stock sectors, crypto, Steam most-played, and league
  standings (Premier League to the NFL) with logos and qualification-zone colors
- Starter templates: one-tap persona decks (Developer, Investor, Sports Fan, and more)
  that you can mix and match
- Localized by country: national news, your biggest city's feed, the local
  league table, property, business and deals cards seed automatically from IP
- Local weather at a glance
- Backend: OAuth2 and web-session auth, organizations, API tokens

## Architecture

One monorepo:

| Path | Stack | Holds |
| --- | --- | --- |
| `server/` | Python 3.14, FastAPI | API, SQLAlchemy, Alembic, Dramatiq workers, Redis |
| `clients/apps/web/` | Next.js | News deck (web) |
| `clients/apps/app/` | Expo, React Native | Mobile app (iOS and Android) |
| `clients/packages/client/` | TypeScript | API client generated from OpenAPI |
| `clients/packages/orbit/` | StyleX | Design system for the web app |

## Getting started

Needs Docker, [uv](https://docs.astral.sh/uv/) and [pnpm](https://pnpm.io).

```bash
./dev/setup-environment        # generate .env files

# Backend at http://127.0.0.1:8000 (from server/)
docker compose up -d           # Postgres, Redis, Minio
uv sync
uv run task generate_dev_jwks
uv run task emails
uv run alembic upgrade head
uv run task api                # API
uv run task worker             # background jobs (second terminal)

# Frontend at http://127.0.0.1:3000 (from clients/)
pnpm install && pnpm dev
```

Changed the API? Run `pnpm run generate` in `clients/packages/client` to update
the client.

## Configuration

`./dev/setup-environment` writes working `.env` files and the app runs out of the
box; the news deck itself needs no external services.

Optional analytics run through [Tinybird](https://www.tinybird.co)
(`OUTCEPTION_TINYBIRD_*` in `server/.env`, kept out of version control); unset,
analytics fall back to Postgres counters.

## Developing

```bash
# Backend (from server/)
uv run task test                               # tests
uv run task lint && uv run task lint_types     # ruff + mypy
uv run alembic revision --autogenerate -m "..."  # new migration

# Frontend
cd clients/apps/web && pnpm typecheck          # web
cd clients/apps/app && pnpm typecheck          # mobile
```

## Contributing

Issues and pull requests are welcome. For bigger changes, open an issue first.

## License

Apache License 2.0. See [LICENSE](LICENSE).
