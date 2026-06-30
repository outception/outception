# Outception

A live news wall with pay-to-promote. Read the headlines for free, or pay to
feature your post at the top of a topic for a while.

## What it is

Outception is two things in one app:

A public news wall. An open, no-login feed that pulls headlines from 250+ sources
(Hacker News, Reddit, mainstream news, plus tech, finance, sports, science,
gaming and more) and lays them out in topic columns. Open it and read.

Pay-to-promote. Signed-in users can buy a topic's featured slot for a block of
time. Slots run as a first-come queue with one promotion live per topic at a
time, and the post shows up as a labelled "Promoted" card on the wall. Payment
goes through an external payment provider and is confirmed with a signed webhook,
so a promotion only goes live once the payment clears.

## Features

- Public news wall on web and mobile, organised by topic
- Sign in, compose a promotion, check out, and it goes live
- Promotion queue with a clear lifecycle: pending, queued, active, expired
- Analytics for spend, impressions, clicks and CTR, with an optional
  [Tinybird](https://www.tinybird.co) pipeline for per-day time series
- Promoter dashboard on web and an analytics screen on mobile
- OAuth2 and web-session auth, organizations, and API tokens

## Architecture

A single monorepo:

| Path | Stack | What it holds |
| --- | --- | --- |
| `server/` | Python 3.14, FastAPI | API (`outception`), SQLAlchemy, Alembic, Dramatiq workers, Redis |
| `clients/apps/web/` | Next.js | Public news wall and promoter dashboard |
| `clients/apps/app/` | Expo, React Native | News feed, promote flow and analytics (iOS and Android) |
| `clients/packages/client/` | TypeScript | API client generated from the backend OpenAPI |
| `clients/packages/orbit/` | | Orbit design system used by the web app |

## Getting started

You need Docker, [uv](https://docs.astral.sh/uv/) and [pnpm](https://pnpm.io).

```bash
./dev/setup-environment        # generates your .env files

# Backend at http://127.0.0.1:8000 (run from server/)
docker compose up -d           # Postgres, Redis, Minio
uv sync
uv run task generate_dev_jwks
uv run task emails
uv run alembic upgrade head
uv run task api                # the API
uv run task worker             # background jobs (second terminal)

# Frontend at http://127.0.0.1:3000 (run from clients/)
pnpm install && pnpm dev
```

After changing the API, regenerate the typed client with `pnpm run generate` in
`clients/packages/client`.

## Configuration

Promotions and analytics are configured in `server/.env`. Keep secrets there and
do not commit the file.

```bash
# Promotions (external payment gateway)
OUTCEPTION_PROMOTION_PRODUCT_ID=""          # a pay-what-you-want product on your gateway org
OUTCEPTION_PAYMENT_GATEWAY_BASE_URL="https://api.polar.sh"
OUTCEPTION_PAYMENT_GATEWAY_ACCESS_TOKEN=""
OUTCEPTION_PAYMENT_GATEWAY_WEBHOOK_SECRET=""

# Optional: Tinybird analytics pipeline
OUTCEPTION_TINYBIRD_API_URL=""
OUTCEPTION_TINYBIRD_API_TOKEN=""
```

Leave them blank and the app still runs. The news wall works as usual, paid
checkout stays off, and analytics fall back to Postgres counters.

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

Issues and pull requests are welcome. For anything bigger, open an issue first so
we can discuss it.

## License

Apache License 2.0. See [LICENSE](LICENSE).
