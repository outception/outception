<div align="center">

# Outception

### A live wall of the world's news — and a spot you can pay to stand on.

Read the headlines for free. When you've got something worth seeing, pay to
pin it to the top of any topic for a while.

</div>

---

## What is this?

Outception is two things sharing one home:

- **A news wall.** An open, no-login feed that pulls headlines from 250+ sources —
  Hacker News, Reddit, mainstream news, plus tech, finance, sports, science,
  gaming and more — and lays them out in tidy topic columns. Just open it and read.

- **Pay-to-promote.** Got a post you want people to notice? Sign in, pick a topic,
  and buy its featured slot for a block of time. Slots run as a fair first-come
  queue (one promotion live per topic at a time), and your post shows up as a
  clearly-labelled **"Promoted"** card on the wall. Payment goes through an
  external payment provider and is confirmed with a signed webhook, so a promotion
  only goes live once the money's actually in.

That's the whole idea: the news is free, attention is the thing you can buy.

## Highlights

- 📰 **Public news wall** on web and mobile, organised by topic
- 💸 **Promote in a few clicks** — sign in, compose, checkout, done
- 🎟️ **Fair queue** — promotions move through `pending → queued → active → expired`
- 📊 **Real analytics** — spend, impressions, clicks and CTR, with an optional
  [Tinybird](https://www.tinybird.co) pipeline for day-by-day time series
- 📈 **Dashboards** — a promoter dashboard on web and an analytics screen on mobile
- 🔐 **Accounts done right** — OAuth2 / web-session auth, organizations, API tokens

## How it's built

It's a single monorepo:

| Where | Stack | What lives there |
| --- | --- | --- |
| `server/` | Python 3.14 · FastAPI | The API (`outception`), SQLAlchemy, Alembic, Dramatiq workers, Redis |
| `clients/apps/web/` | Next.js | The public news wall + the promoter dashboard |
| `clients/apps/app/` | Expo · React Native | News feed, promote flow and analytics for iOS + Android |
| `clients/packages/client/` | TypeScript | API client, generated from the backend's OpenAPI |
| `clients/packages/orbit/` | — | Orbit, the design system the web app is built on |

## Getting started

You'll need Docker, [uv](https://docs.astral.sh/uv/) and [pnpm](https://pnpm.io).

```bash
./dev/setup-environment        # generates your .env files

# Backend → http://127.0.0.1:8000 (run from server/)
docker compose up -d           # Postgres, Redis, Minio
uv sync
uv run task generate_dev_jwks
uv run task emails
uv run alembic upgrade head
uv run task api                # the API
uv run task worker             # background jobs (in a second terminal)

# Frontend → http://127.0.0.1:3000 (run from clients/)
pnpm install && pnpm dev
```

Changed the API? Regenerate the typed client with `pnpm run generate` in
`clients/packages/client`.

## Configuration

Promotions and analytics are wired up through `server/.env` — keep your secrets
there and never commit it:

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

Leave them blank and everything still runs — the news wall works as usual,
paid checkout simply stays switched off, and analytics fall back to plain
Postgres counters.

## Developing

```bash
# Backend (from server/)
uv run task test                               # tests
uv run task lint && uv run task lint_types     # ruff + mypy
uv run alembic revision --autogenerate -m "…"  # new migration

# Frontend
cd clients/apps/web && pnpm typecheck          # web
cd clients/apps/app && pnpm typecheck          # mobile
```

## Contributing

Issues and pull requests are welcome. If you're planning something bigger, open
an issue first so we can talk it through.

## License

Released under the [Apache License 2.0](LICENSE).
