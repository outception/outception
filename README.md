# Outception

A live news wall with pay-to-promote. Read the news for free, or pay to feature
your post at the top of a topic.

## What it is

Two things in one app:

- **News wall.** An open, no-login feed of headlines from 800+ sources (Hacker
  News, Reddit, mainstream news, tech, finance, sports, science, gaming, and
  more), laid out in topic columns.
- **Pay-to-promote.** Sign in, pick a topic, and buy its featured slot for a set
  time. Slots run as a queue, one promotion per topic at a time, shown as a
  "Promoted" card. Payment runs through an external gateway and is confirmed by a
  signed webhook, so a post only goes live once the payment clears.

## Features

- News wall on web and mobile, by topic
- Compose a promotion, check out, go live
- Promotion lifecycle: pending, queued, active, expired
- Analytics: spend, impressions, clicks, CTR (optional
  [Tinybird](https://www.tinybird.co) pipeline for daily time series)
- Promoter dashboard (web) and analytics screen (mobile)
- OAuth2 and web-session auth, organizations, API tokens

## Architecture

One monorepo:

| Path | Stack | Holds |
| --- | --- | --- |
| `server/` | Python 3.14, FastAPI | API, SQLAlchemy, Alembic, Dramatiq workers, Redis |
| `clients/apps/web/` | Next.js | News wall and promoter dashboard |
| `clients/apps/app/` | Expo, React Native | Mobile app (iOS and Android) |
| `clients/packages/client/` | TypeScript | API client generated from OpenAPI |
| `clients/packages/orbit/` | | Design system for the web app |

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

Set these in `server/.env` (keep secrets there, do not commit it):

```bash
# Promotions (external payment gateway)
OUTCEPTION_PROMOTION_PRODUCT_ID=""          # pay-what-you-want product on your gateway org
OUTCEPTION_PAYMENT_GATEWAY_BASE_URL="https://api.polar.sh"
OUTCEPTION_PAYMENT_GATEWAY_ACCESS_TOKEN=""
OUTCEPTION_PAYMENT_GATEWAY_WEBHOOK_SECRET=""

# Optional: Tinybird analytics
OUTCEPTION_TINYBIRD_API_URL=""
OUTCEPTION_TINYBIRD_API_TOKEN=""
```

Leave them blank and the app still runs: the news wall works, paid checkout is
off, and analytics use Postgres counters.

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
