# Deployment / Go-Live Checklist

Everything below is **config and external setup the codebase can't supply itself**.
The app is feature-complete, tested, and type-clean; these are the inputs needed to
run it for real. All backend settings are read from `server/.env` with the `POLAR_`
prefix (e.g. the setting `SECRET` → env var `POLAR_SECRET`).

## 1. Backend — required secrets & infra (`server/.env`)

| Env var | Notes |
| --- | --- |
| `POLAR_ENV` | `production` or `sandbox`. The app **refuses to boot** in these envs if `POLAR_SECRET` is still the dev default (see below). |
| `POLAR_SECRET` | **Strong, unique value.** Keys all token hashing (PATs, OAuth codes, OTPs, sessions). Must not be the dev default. |
| `POLAR_JWKS` | Path to a JWKS file. Generate one with `uv run task generate_dev_jwks`, or supply a real key set. |
| `POLAR_POSTGRES_*` | `USER`, `PWD`, `HOST`, `PORT`, `DATABASE` (+ optional `POSTGRES_READ_*` for a read replica). |
| `POLAR_REDIS_HOST` / `_PORT` / `_DB` | Redis connection. |
| `POLAR_S3_FILES_BUCKET_NAME`, `POLAR_AWS_ACCESS_KEY_ID`, `POLAR_AWS_SECRET_ACCESS_KEY` | Object storage (S3/MinIO). |
| `POLAR_BASE_URL`, `POLAR_FRONTEND_BASE_URL` | The API and web base URLs for this deployment. |
| `POLAR_CORS_ORIGINS` | Allowlist of credentialed web origins. |

Run migrations before first boot: `cd server && uv run alembic upgrade head`.

## 2. Promotions — polar.sh payment gateway (`server/.env`)

Promotion checkout is disabled until these are set (the create endpoint returns 503):

| Env var | Notes |
| --- | --- |
| `POLAR_PROMOTION_PRODUCT_ID` | A **pay-what-you-want** product on your polar.sh org. |
| `POLAR_PAYMENT_GATEWAY_ACCESS_TOKEN` | polar.sh API token. |
| `POLAR_PAYMENT_GATEWAY_WEBHOOK_SECRET` | Standard-Webhooks secret for the order webhook. |
| `POLAR_PAYMENT_GATEWAY_BASE_URL` | Defaults to `https://api.polar.sh`. |

Pricing/duration knobs (optional): `POLAR_PROMOTION_PRICE_CENTS` (default 1000),
`POLAR_PROMOTION_BLOCK_MINUTES` (default 10), `POLAR_PROMOTION_IMPRESSION_DEDUP_SECONDS`
(default 600).

> ⚠️ **Underpayment check needs verification.** The order webhook refuses to activate a
> promotion that paid less than `promotion.amount_cents`, reading the amount from the
> order's `total_amount` / `amount` / `subtotal_amount` / `net_amount` field (first
> present). If your real polar.sh `order.*` payload uses a different field name, the
> check fails closed (logs `billing.promotion.no_amount` and refuses a valid payment).
> **Send a sample `order.paid` webhook body** and the exact field can be pinned.
> See `server/polar/billing/service.py::_extract_paid_amount`.

## 3. Email — transactional sender (`server/.env`)

| Env var | Notes |
| --- | --- |
| `POLAR_EMAIL_SENDER` | `resend` for real email (default `logger` just logs). |
| `POLAR_RESEND_API_KEY` | Resend API key. |
| `POLAR_EMAIL_FROM_DOMAIN` | A domain **you control** (DNS/SPF/DKIM). Default `notifications.polar.sh` is a placeholder. |
| `POLAR_EMAIL_FROM_LOCAL` | Local part (default `mail`). |
| `POLAR_EMAIL_DEFAULT_REPLY_TO_EMAIL_ADDRESS` | Reply-to address on your domain (default `support@polar.sh` is a placeholder). |

Display names (`EMAIL_FROM_NAME`, `EMAIL_DEFAULT_REPLY_TO_NAME`) already default to
"Outception" / "Outception Support".

## 4. Optional — Tinybird analytics (`server/.env`)

Without these, promotion analytics fall back to Postgres-only counters.

`POLAR_TINYBIRD_API_URL`, `POLAR_TINYBIRD_API_TOKEN`, `POLAR_TINYBIRD_READ_TOKEN`.

## 5. Web frontend (`clients/apps/web`)

- **Production domain** — `src/app/(main)/layout.tsx` still has `metadataBase` and
  `alternates.canonical` set to `https://polar.sh/`. Point these at your real domain
  (they were left as-is rather than guessed).
- **OG/social image** — the Polar-branded OG image was removed. Add an Outception
  social-preview image (static asset or the existing `/api/og` route) and reference it
  in the same metadata block.
- `NEXT_PUBLIC_API_URL` / server URL env → this deployment's backend.

## 6. Mobile app (`clients/apps/app`)

- `auth/oauthConfig.ts` currently points the OAuth flow at **production `polar.sh`**.
  Repoint `discovery` (authorize/token/register/revoke endpoints) and `CLIENT_ID` at
  **this deployment's backend** before mobile auth will work.
- Add `promotions:read` and `promotions:write` to the requested `scopes` array — the
  backend now gates the paid promotion endpoints on those scopes (`promotions:write`
  for create/preferences). The OAuth client registered on the backend must also allow
  those scopes.

## 7. Verify before shipping

```bash
# backend (from server/)
uv run task lint && uv run task lint_types && uv run task test_fast
# frontend (from clients/)
pnpm --filter web typecheck && (cd apps/web && pnpm lint:only && npx vitest run && npx next build)
pnpm --filter @polar-sh/app typecheck && (cd apps/app && pnpm lint && npx jest)
```

All of the above are green as of the latest commit. After setting `POLAR_SECRET`,
confirm the app boots in your target env (the strong-secret guard will refuse the
default).
