# Deployment / Go-Live Checklist

Everything below is **config and external setup the codebase can't supply itself**.
The app is feature-complete, tested, and type-clean; these are the inputs needed to
run it for real. All backend settings are read from `server/.env` with the `OUTCEPTION_`
prefix (e.g. the setting `SECRET` → env var `OUTCEPTION_SECRET`).

## 1. Backend — required secrets & infra (`server/.env`)

| Env var | Notes |
| --- | --- |
| `OUTCEPTION_ENV` | `production`. The app **refuses to boot** in production if `OUTCEPTION_SECRET` is still the dev default (see below). |
| `OUTCEPTION_SECRET` | **Strong, unique value.** Keys all token hashing (PATs, OAuth codes, OTPs, sessions). Must not be the dev default. |
| `OUTCEPTION_JWKS` | Path to a JWKS file. Generate one with `uv run task generate_dev_jwks`, or supply a real key set. |
| `OUTCEPTION_POSTGRES_*` | `USER`, `PWD`, `HOST`, `PORT`, `DATABASE` (+ optional `POSTGRES_READ_*` for a read replica). |
| `OUTCEPTION_REDIS_HOST` / `_PORT` / `_DB` | Redis connection. |
| `OUTCEPTION_S3_FILES_BUCKET_NAME`, `OUTCEPTION_AWS_ACCESS_KEY_ID`, `OUTCEPTION_AWS_SECRET_ACCESS_KEY` | Object storage (S3/MinIO). |
| `OUTCEPTION_BASE_URL`, `OUTCEPTION_FRONTEND_BASE_URL` | The API and web base URLs for this deployment. |
| `OUTCEPTION_CORS_ORIGINS` | Allowlist of credentialed web origins. |

Run migrations before first boot: `cd server && uv run alembic upgrade head`.

## 2. Email — transactional sender (`server/.env`)

| Env var | Notes |
| --- | --- |
| `OUTCEPTION_EMAIL_SENDER` | `resend` for real email (default `logger` just logs). |
| `OUTCEPTION_RESEND_API_KEY` | Resend API key. |
| `OUTCEPTION_EMAIL_FROM_DOMAIN` | A domain **you control** (DNS/SPF/DKIM). Default `notifications.outception.com` is a placeholder. |
| `OUTCEPTION_EMAIL_FROM_LOCAL` | Local part (default `mail`). |
| `OUTCEPTION_EMAIL_DEFAULT_REPLY_TO_EMAIL_ADDRESS` | Reply-to address on your domain (default `support@outception.com` is a placeholder). |

Display names (`EMAIL_FROM_NAME`, `EMAIL_DEFAULT_REPLY_TO_NAME`) already default to
"Outception" / "Outception Support".

## 3. Optional — Tinybird analytics (`server/.env`)

Without these, promotion analytics fall back to Postgres-only counters.

`OUTCEPTION_TINYBIRD_API_URL`, `OUTCEPTION_TINYBIRD_API_TOKEN`, `OUTCEPTION_TINYBIRD_READ_TOKEN`.

## 4. Web frontend (`clients/apps/web`) — all env vars, no code edits

| Env var | Notes |
| --- | --- |
| `NEXT_PUBLIC_FRONTEND_BASE_URL` | Your web domain. Now **drives `metadataBase` + canonical** automatically (no longer hardcoded). |
| `NEXT_PUBLIC_API_URL` | This deployment's backend. |
| `NEXT_PUBLIC_ENVIRONMENT` | `production`. |

Only remaining manual item: **OG/social image** — the Outception-branded image was removed.
Add an Outception social-preview image (a static asset, or reference the existing
`/api/og` route) in the metadata block of `src/app/(main)/layout.tsx`.

## 5. Mobile app (`clients/apps/app`) — all env vars, no code edits

`auth/oauthConfig.ts` is now fully env-driven (defaults to the local dev backend, and
requests the scopes listed in that file). Set:

| Env var | Notes |
| --- | --- |
| `EXPO_PUBLIC_OUTCEPTION_SERVER_URL` | API base, e.g. `https://api.yourdomain`. |
| `EXPO_PUBLIC_OUTCEPTION_WEB_URL` | Web base, e.g. `https://app.yourdomain`. |
| `EXPO_PUBLIC_OAUTH_CLIENT_ID` | A **public** OAuth client registered on your backend (`<web>/dashboard/account/developer`), redirect URI `outception://oauth/callback`, granting the scopes listed in `oauthConfig.ts`. |

## 6. Verify before shipping

```bash
# backend (from server/)
uv run task lint && uv run task lint_types && uv run task test_fast
# frontend (from clients/)
pnpm --filter web typecheck && (cd apps/web && pnpm lint:only && npx vitest run && npx next build)
pnpm --filter @outception-com/app typecheck && (cd apps/app && pnpm lint && npx jest)
```

All of the above are green as of the latest commit. After setting `OUTCEPTION_SECRET`,
confirm the app boots in your target env (the strong-secret guard will refuse the
default).
