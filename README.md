# Outception

A live news wall where your feed is your choice. Pick the sources and topics you
care about and read the news for free, supported by ads.

## What it is

An open, no-login **live news wall**: a continuously updated feed of headlines
from 2,500+ sources (Hacker News, The Verge, TechCrunch, Ars Technica, BBC News,
The Guardian, NPR, Bloomberg, GitHub, Product Hunt, Steam, ESPN, and more), laid
out in topic columns: news, world, sports, finance, science, entertainment,
tech, social, and betting.

It's free to read, monetized with ads: **Google AdMob** on mobile and **Google
AdSense** on the web.

## Features

- News wall on web and mobile, laid out by topic
- Follow, filter, and search across 2,500+ sources; no account required to read
- Local weather at a glance
- Ad-supported: AdMob on mobile, AdSense on web
- Backend: OAuth2 and web-session auth, organizations, API tokens

## Architecture

One monorepo:

| Path | Stack | Holds |
| --- | --- | --- |
| `server/` | Python 3.14, FastAPI | API, SQLAlchemy, Alembic, Dramatiq workers, Redis |
| `clients/apps/web/` | Next.js | News wall (web) |
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
box; the news wall itself needs no external services.

Ads are configured client-side:

- **Mobile (AdMob):** set the app and unit IDs per build profile in
  `clients/apps/app/eas.json` (`ADMOB_*_APP_ID`, `EXPO_PUBLIC_ADMOB_BANNER_*`).
  Dev builds fall back to Google's public test IDs.
- **Web (AdSense):** set `NEXT_PUBLIC_ADSENSE_CLIENT` and
  `NEXT_PUBLIC_ADSENSE_SLOT_WALL`. Leave them unset and web ads stay off.

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
