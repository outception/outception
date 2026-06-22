<div align="center">

# Outception

**A live news wall with pay-to-promote.**

Browse headlines from 250+ sources for free. Pay to feature a post in any
topic — promotion payments are handled externally by [polar.sh](https://polar.sh).

</div>

<hr />

## What it is

Outception is a two-part product:

- **News wall** — a public, unauthenticated feed of headlines aggregated from
  250+ sources (Hacker News, Reddit, mainstream news, tech, finance, sports,
  science, gaming, …), organised into topic columns.
- **Paid promotions** — signed-in users buy a category's featured slot for a
  block of time (FIFO queue, one active promotion per category). Promotions
  surface as "Promoted" cards on the wall. Payment runs through **polar.sh as
  an external merchant**, confirmed via a signed webhook.

It started as a fork of the [Polar](https://github.com/polarsource/polar)
codebase; the Merchant-of-Record stack has been removed and the auth, payments,
and analytics infrastructure repurposed for promotions.

## Features

- Public news wall (web + mobile) with topic columns and per-topic promotions
- Login-gated promotion compose → polar.sh hosted checkout → signed webhook
- Promotion lifecycle queue (pending → queued → active → expired)
- Analytics: spend, impressions, clicks and CTR — counters in Postgres, with an
  optional **Tinybird** event pipeline for per-day time-series
- Promoter dashboard (web) and analytics screen (mobile) charting the series
- OAuth2 / web-session auth, organizations, API tokens

## Architecture

Monorepo:

| Path | Stack | What |
| --- | --- | --- |
| `server/` | Python 3.14 / FastAPI | API (`polar` package), SQLAlchemy, Alembic, Dramatiq workers, Redis |
| `clients/apps/web/` | Next.js | News wall (public home) + promoter dashboard |
| `clients/apps/app/` | Expo / React Native | News feed + promote + analytics (iOS/Android) |
| `clients/packages/client/` | TypeScript | API client generated from the backend OpenAPI |
| `clients/packages/orbit/` | — | Orbit design system (web) |

See `AGENTS.md`, `server/AGENTS.md`, and `clients/AGENTS.md` for conventions.

## Quick start

```bash
./dev/setup-environment        # generate .env files

# Backend (http://127.0.0.1:8000) — from server/
docker compose up -d           # PostgreSQL, Redis, Minio
uv sync
uv run task generate_dev_jwks
uv run task emails
uv run alembic upgrade head
uv run task api                # API server
uv run task worker             # background worker (separate terminal)

# Frontend (http://127.0.0.1:3000) — from clients/
pnpm install && pnpm dev
```

After changing the API, regenerate the client: `pnpm run generate` in
`clients/packages/client`.

## Configuration

Promotion payments and analytics are configured via `server/.env` (secrets live
there only — never committed):

```bash
# Promotions via polar.sh (external)
POLAR_PROMOTION_PRODUCT_ID=""          # pay-what-you-want product on your polar.sh org
POLAR_PAYMENT_GATEWAY_BASE_URL="https://api.polar.sh"
POLAR_PAYMENT_GATEWAY_ACCESS_TOKEN=""
POLAR_PAYMENT_GATEWAY_WEBHOOK_SECRET=""

# Optional: Tinybird analytics pipeline
POLAR_TINYBIRD_API_URL=""
POLAR_TINYBIRD_API_TOKEN=""
```

Without these, the news wall still works and promotion checkout is disabled by
design; analytics fall back to Postgres-only counters.

## Development

```bash
cd server
uv run task test                              # backend tests
uv run task lint && uv run task lint_types    # ruff + mypy
uv run alembic revision --autogenerate -m "…" # new migration

cd clients/apps/web && pnpm typecheck         # web types
cd clients/apps/app && pnpm typecheck         # mobile types
```

## License

Apache License 2.0.
