# Deployment configuration

What must be set for a production deployment, and why. The host-level runbook
(Hetzner, Cloudflare, Docker Compose) is in [`deploy/README.md`](./deploy/README.md).

Backend settings are read from `server/.env` with the `OUTCEPTION_` prefix
(setting `SECRET` is env var `OUTCEPTION_SECRET`).

## Backend (`server/.env`)

| Env var | Why |
| --- | --- |
| `OUTCEPTION_ENV=production` | Enables production guards. The app refuses to boot in production while `OUTCEPTION_SECRET` is the dev default. |
| `OUTCEPTION_SECRET` | Keys all token hashing (PATs, OAuth codes, OTPs, sessions). Must be strong and unique. |
| `OUTCEPTION_JWKS` | Path to the JWKS file used to sign tokens. Generate with `uv run task generate_dev_jwks` or supply your own key set. |
| `OUTCEPTION_POSTGRES_USER`, `_PWD`, `_HOST`, `_PORT`, `_DATABASE` | Primary database. `OUTCEPTION_POSTGRES_READ_*` optionally points reads at a replica. |
| `OUTCEPTION_REDIS_HOST`, `_PORT`, `_DB` | Job broker and cache. |
| `OUTCEPTION_S3_FILES_BUCKET_NAME`, `OUTCEPTION_AWS_ACCESS_KEY_ID`, `OUTCEPTION_AWS_SECRET_ACCESS_KEY` | Object storage (S3 or any S3-compatible service). |
| `OUTCEPTION_BASE_URL`, `OUTCEPTION_FRONTEND_BASE_URL` | Public API and web URLs; used in links, OAuth redirects and emails. |
| `OUTCEPTION_CORS_ORIGINS` | Allowlist of web origins that may send credentialed requests. Must include the web URL. |

Run `cd server && uv run alembic upgrade head` before the first boot and after every deploy.

## Email (`server/.env`)

| Env var | Why |
| --- | --- |
| `OUTCEPTION_EMAIL_SENDER=resend` | Sends real email. The default `logger` only logs. |
| `OUTCEPTION_RESEND_API_KEY` | Resend API key. |
| `OUTCEPTION_EMAIL_FROM_DOMAIN` | A domain you control with SPF/DKIM configured. The default is a placeholder. |
| `OUTCEPTION_EMAIL_FROM_LOCAL` | Local part of the sender address (default `mail`). |
| `OUTCEPTION_EMAIL_DEFAULT_REPLY_TO_EMAIL_ADDRESS` | Reply-to address on your domain. The default is a placeholder. |

`EMAIL_FROM_NAME` and `EMAIL_DEFAULT_REPLY_TO_NAME` default to "Outception" and "Outception Support".

## Tinybird (optional, `server/.env`)

`OUTCEPTION_TINYBIRD_API_URL`, `OUTCEPTION_TINYBIRD_API_TOKEN`, `OUTCEPTION_TINYBIRD_READ_TOKEN`.
Without them promotion analytics use Postgres counters only.

## Web (`clients/apps/web`)

| Env var | Why |
| --- | --- |
| `NEXT_PUBLIC_FRONTEND_BASE_URL` | Public web URL. Drives `metadataBase` and canonical URLs. |
| `NEXT_PUBLIC_API_URL` | Backend URL the browser calls. |
| `NEXT_PUBLIC_ENVIRONMENT=production` | Selects production config (analytics, error reporting). |

The social preview image is not set. Add one in the metadata block of
`src/app/(main)/layout.tsx`, either as a static asset or via the `/api/og` route.

## Mobile (`clients/apps/app`)

`auth/oauthConfig.ts` reads its endpoints and client id from the environment and
defaults to the local dev backend.

| Env var | Why |
| --- | --- |
| `EXPO_PUBLIC_OUTCEPTION_SERVER_URL` | API base URL. |
| `EXPO_PUBLIC_OUTCEPTION_WEB_URL` | Web base URL. |
| `EXPO_PUBLIC_OAUTH_CLIENT_ID` | A public OAuth client registered on your backend (`<web>/dashboard/account/developer`) with redirect URI `outception://oauth/callback` and the scopes listed in `oauthConfig.ts`. |

## Verification

```bash
# backend (from server/)
uv run task lint && uv run task lint_types && uv run task test_fast
# web (from clients/)
pnpm --filter web typecheck && (cd apps/web && pnpm lint:only && npx vitest run && npx next build)
# mobile (from clients/)
pnpm --filter @outception-com/app typecheck && (cd apps/app && pnpm lint && npx jest)
```

After setting `OUTCEPTION_SECRET`, boot the API once in the target environment
to confirm the strong-secret guard passes.
