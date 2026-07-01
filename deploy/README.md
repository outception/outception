# Deploying Outception on Hetzner + Cloudflare + R2

A single-host Docker Compose deployment: PostgreSQL, Redis, the API, a background
worker (with the scheduler embedded), the Next.js web app, and Caddy for TLS.
Object storage is Cloudflare R2 (S3-compatible — no code changes). DNS + CDN is
Cloudflare.

```
                    ┌─────────── Cloudflare (DNS, proxy, TLS edge) ───────────┐
   outception.com ──┤  api.outception.com ─────────────┐                      │
                    └──────────────────────────────────┼──────────────────────┘
                                                        ▼
                              Hetzner VPS ── Caddy :443 ──┬── web  :3000 (Next.js)
                                                          └── api  :10000 (FastAPI)
                                                  api ─┬─ db    (Postgres 15)
                                                       ├─ redis (broker + cache)
                                                  worker (dramatiq + scheduler)
                                          object storage ─→ Cloudflare R2
```

## Files

| File | Purpose |
| --- | --- |
| `docker-compose.prod.yml` | All services |
| `web.Dockerfile` | Next.js standalone production image |
| `caddy.Dockerfile` | Caddy built with the Cloudflare DNS plugin |
| `Caddyfile` | Reverse proxy + automatic TLS |
| `.env.prod.example` | Copy to `.env.prod` and fill in |
| `../.github/workflows/deploy-hetzner.yml` | Build → push GHCR → SSH deploy |

---

## 1. Cloudflare R2 (object storage)

1. R2 → create an API token (Access Key ID + Secret).
2. Note your account ID → endpoint is `https://<account-id>.r2.cloudflarestorage.com`.
3. (Optional) create buckets only if you enable observability log/profile export —
   the news/promotion product itself stores no user files.
4. Put the endpoint + keys into `.env.prod` (`OUTCEPTION_S3_ENDPOINT_URL`,
   `OUTCEPTION_AWS_ACCESS_KEY_ID/SECRET`, `OUTCEPTION_AWS_REGION=auto`).

## 2. Cloudflare DNS + TLS

1. Add **A records** for `outception.com` and `api.outception.com` → your Hetzner
   server IP. Proxied (orange cloud) is fine.
2. SSL/TLS mode → **Full (strict)**.
3. Create an API token with **Zone → DNS → Edit** on the zone → `CF_API_TOKEN`
   in `.env.prod`. Caddy uses it for the ACME DNS-01 challenge, so TLS works even
   behind the proxy.

## 3. Hetzner host (one-time)

```bash
# Ubuntu 24.04 box. Install Docker + compose plugin:
curl -fsSL https://get.docker.com | sh

# Clone the repo and configure:
git clone https://github.com/outception/outception.git
cd outception/deploy
cp .env.prod.example .env.prod
$EDITOR .env.prod          # fill EVERY blank — see checklist below
```

### Generate the secrets

```bash
# OUTCEPTION_SECRET — strong random value:
openssl rand -hex 32

# OUTCEPTION_JWKS — a JWKS *file* (RS256), mounted into the containers.
# Generate one (from server/) and place it where compose expects it:
cd server && uv run task generate_dev_jwks      # writes server/.jwks.json
mkdir -p ../deploy/secrets && mv .jwks.json ../deploy/secrets/jwks.json
# .env.prod already points OUTCEPTION_JWKS at /run/secrets/jwks.json and
# CURRENT_JWK_KID at "outception_dev" (the kid the generator uses).
```

`deploy/secrets/` is gitignored — the keypair never gets committed.

## 4. First boot

```bash
cd outception/deploy
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```

- `migrate` runs `alembic upgrade head` automatically before `api`/`worker` start.
- Watch logs: `docker compose --env-file .env.prod -f docker-compose.prod.yml logs -f`
- Health: `curl https://api.outception.com/healthz` → `{"status":"ok"}`

> The `--env-file .env.prod` flag is **required** on every compose command — it
> drives `${...}` interpolation (db creds, domains, image tag). The app services
> also load `.env.prod` internally via `env_file:`.

## 5. Continuous deploys (optional)

The `deploy-hetzner.yml` workflow builds both images, pushes to GHCR, and runs
`docker compose pull && up -d` over SSH on every push to `main`.

Set repo **secrets**: `SSH_HOST`, `SSH_USER`, `SSH_PRIVATE_KEY`, `GHCR_PAT`
(host pull token). Set repo **variables**: `NEXT_PUBLIC_API_URL`,
`NEXT_PUBLIC_FRONTEND_BASE_URL`, `DEPLOY_PATH` (the `deploy/` path on the host).

With CI in use, drop `--build` from the host (it pulls prebuilt images by
`IMAGE_TAG`).

---

## Critical config (auth breaks silently if wrong)

- **Cookie domains** must be your real domain (`.outception.com`), not the
  `127.0.0.1` defaults — otherwise login cookies aren't valid on the site.
- **`OUTCEPTION_CORS_ORIGINS`** must include `https://outception.com`.
- **`OUTCEPTION_SECRET`** must be strong — the app refuses to boot in production
  with the dev default.
- **OAuth redirect URIs** in Google/GitHub/Apple consoles must point at
  `https://api.outception.com/...`.
- **Payment webhook**: register the gateway's order webhook at
  `https://api.outception.com/v1/billing/webhook` (or the configured path) and
  set `OUTCEPTION_PAYMENT_GATEWAY_WEBHOOK_SECRET`.

## Scaling notes

- The `worker` runs the scheduler **embedded** and must stay at **1 replica**
  (else cron jobs double-fire). To scale workers, remove
  `-f outception.worker.scheduler:start` from the worker command and add a
  separate single-replica scheduler service.
- Postgres/Redis run on the same host here. For real load, move Postgres to a
  managed/standalone host and add `OUTCEPTION_POSTGRES_READ_*` for a replica.

## Backups

Point the existing `database_backup*.yml` workflows (or a cron `pg_dump`) at an
R2 bucket using the same S3-compatible credentials.
