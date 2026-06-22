# Outception

A live news wall with pay-to-promote. Public news feed (250+ sources) plus login-gated paid
promotions charged through polar.sh as an external merchant. Monorepo with a Python/FastAPI
backend (package `polar`) and Next.js + Expo frontends. Forked from Polar; the Merchant-of-Record
stack was removed and its auth/payments/analytics repurposed for promotions.

This file is the entry point for AI agents working in this repo: start here, then read the
per-area `AGENTS.md` linked from the Architecture and Conventions sections before writing code.

## General Guidelines

- Do not add comments unless necessary — the code should be self-explanatory.
- Use meaningful variable and function names.
- Follow established conventions and good practices (SOLID, maintainable code).
- Do not modify code unrelated to the task or issue you are working on.

## Architecture

```
polar/
├── server/                 # Python/FastAPI backend — see server/AGENTS.md
│   ├── polar/
│   │   ├── {module}/
│   │   │   ├── endpoints.py     # FastAPI routes
│   │   │   ├── service.py       # Business logic (singleton)
│   │   │   ├── repository.py    # Database queries (SQLAlchemy)
│   │   │   ├── schemas.py       # Pydantic models
│   │   │   └── tasks.py         # Dramatiq background jobs
│   │   ├── models/             # SQLAlchemy models (global, not per-module)
│   │   ├── news/               # Public news aggregation (sources, cache, fetch)
│   │   ├── promotion/          # Pay-to-promote: queue, lifecycle, analytics, events
│   │   └── billing/            # polar.sh hosted checkout + signed webhook
│   └── migrations/             # Alembic database migrations
├── clients/                # Turborepo + pnpm frontend — see clients/AGENTS.md
│   ├── apps/web/               # Next.js dashboard
│   ├── apps/app/               # Expo / React Native (iOS + Android)
│   ├── apps/orbit/             # Orbit design-system showcase
│   ├── packages/orbit/         # Orbit design system (components + tokens)
│   ├── packages/ui/            # Legacy shared components (Radix + Tailwind)
│   ├── packages/client/        # Generated API client + data hooks
│   └── packages/i18n/          # Translations
├── dev/                    # Dev scripts and tooling
├── docs/                   # User/developer docs (Mintlify)
├── sdk/overlay/            # OpenAPI Overlay tweaks for Speakeasy-generated SDKs
└── .claude/                # Claude Code config (settings, hooks, commands)
```

The TypeScript API client is generated from the backend's OpenAPI schema. After changing the
API, run `pnpm run generate` in `clients/packages/client`.

## Setup

```bash
./dev/setup-environment     # generate .env files
# For GitHub integration:
./dev/setup-environment --setup-github-app --backend-external-url https://yourdomain.ngrok.dev
```

**Backend** (http://127.0.0.1:8000) — from `server/`:
```bash
docker compose up -d          # PostgreSQL, Redis, Minio
uv sync                       # install deps
uv run task api               # API server
uv run task worker            # background worker (separate terminal)
```

**Frontend** (http://127.0.0.1:3000) — from `clients/`:
```bash
pnpm install && pnpm dev
```

**Promotions (polar.sh)** — add to `server/.env` to enable promotion checkout:
- `POLAR_PROMOTION_PRODUCT_ID` (pay-what-you-want product on your polar.sh org)
- `POLAR_PAYMENT_GATEWAY_BASE_URL` (default `https://api.polar.sh`)
- `POLAR_PAYMENT_GATEWAY_ACCESS_TOKEN`, `POLAR_PAYMENT_GATEWAY_WEBHOOK_SECRET`

**Tinybird (optional analytics)** — `POLAR_TINYBIRD_API_URL`, `POLAR_TINYBIRD_API_TOKEN`. Without
these, promotion analytics fall back to Postgres-only counters.

**Fresh worktrees** (`.claude/worktrees/`) don't carry `.env` or built artifacts. Before running
tests in a new worktree:
```bash
cd server
./dev/setup-environment       # generates .env
uv run task generate_dev_jwks # creates .jwks.json
uv run task emails            # builds emails/bin/react-email-pkg
```
Without these, pytest fails at config load with `JWKS` and `EMAIL_RENDERER_BINARY_PATH` errors.

## Development Workflow

**Always prefix Python commands with `uv run`** — it guarantees the correct Python (3.14),
project dependencies, environment variables, and virtualenv context.

```bash
cd server
uv run task test                                          # backend tests (pnpm test for frontend)
uv run task lint && uv run task lint_types                # lint + type-check
uv run alembic revision --autogenerate -m "description"   # generate a migration from model changes
uv run alembic upgrade head                               # apply migrations
```

See `server/AGENTS.md` for backend command and testing specifics.

## Conventions

Detailed, review-enforced patterns live next to the code — read the relevant file before writing:

- **Backend** → `server/AGENTS.md`: modular structure, repository/service/endpoint patterns,
  `lazy="raise"` relationships, status-coded `PolarError`, endpoints return ORM models,
  authentication (`AuthSubject` + scopes).
- **Frontend** → `clients/AGENTS.md`: Orbit `<Box />` design system (raw Tailwind is **deprecated**
  for layout/spacing/color/etc.), TanStack Query for data, Zustand for state, 250-line `max-lines` limit.

**i18n:** add new translatable strings only to `clients/packages/i18n/src/locales/en.ts` — a CI
job auto-translates the rest. Don't edit other locale files. (More in `clients/AGENTS.md`.)

## Custom Commands

- `/polar-code-review` — comprehensive review with 3 parallel agents (security, conventions, simplification).

## Documentation

- **Handbook**: https://handbook.polar.sh/engineering/
- **Design docs**: https://handbook.polar.sh/engineering/design-documents/
- **API guidelines**: https://handbook.polar.sh/engineering/rest-api-guidelines
- **User/developer docs**: `docs/` (Mintlify) — `cd docs && pnpm dev` to serve locally.

## Key Integrations

- **polar.sh**: external merchant for promotion payments (hosted checkout + signed webhook). Needs
  product id + access token + webhook secret in `server/.env`.
- **Tinybird** (optional): promotion event ingestion + analytics pipe. Falls back to Postgres.
- **GitHub / Google / Apple**: OAuth2 authentication.
- **S3 / Minio**: object storage.
- **Redis**: cache and job queue.
- **PostgreSQL**: primary database.
