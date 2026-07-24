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

Create an Ubuntu 24.04 server in the [Hetzner Cloud
Console](https://console.hetzner.com/) (a CPX21/CPX31 is enough to start), add
your SSH key, and note its IP. Then bootstrap it with the provisioning script —
it installs Docker + compose, creates the unprivileged `deploy` user the CI logs
in as, clones the repo to `/opt/outception`, and opens the firewall:

```bash
# On the server, as root (DEPLOY_SSH_PUBKEY = the CI deploy key's PUBLIC half):
curl -fsSL https://raw.githubusercontent.com/outception/outception/main/deploy/provision.sh \
  | DEPLOY_SSH_PUBKEY="ssh-ed25519 AAAA... ci-deploy" bash
```

It's idempotent and prints the exact next steps. Then, as the `deploy` user:

```bash
cd /opt/outception/deploy
cp .env.prod.example .env.prod
$EDITOR .env.prod          # fill EVERY blank — see checklist below
```

(To do the bootstrap by hand instead, run `curl -fsSL https://get.docker.com |
sh`, create a user, and `git clone` the repo yourself.)

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

On every push to `main`, the `deploy-hetzner.yml` workflow builds both images and
pushes them to GHCR, then over SSH it: checks the host out to the exact commit
(so compose / Caddyfile / env changes ship too — `.env.prod` and `secrets/` are
gitignored and left untouched), `docker compose pull && up -d`, and **health-gates
the API `/healthz` — rolling back to the previous image if it doesn't come up.**

Set repo **secrets**: `SSH_HOST`, `SSH_USER`, `SSH_PRIVATE_KEY`, `GHCR_PAT`
(host pull token, `read:packages`). Set repo **variables**: `NEXT_PUBLIC_API_URL`,
`NEXT_PUBLIC_FRONTEND_BASE_URL`, `DEPLOY_PATH` (the `deploy/` path on the host,
e.g. `/opt/outception/deploy`).

Every push to `main` deploys — the health check + rollback is the safety net, so
no separate CI gate is required.

---

## Critical config (auth breaks silently if wrong)

- **Cookie domains** must be your real domain (`.outception.com`), not the
  `127.0.0.1` defaults — otherwise login cookies aren't valid on the site.
- **`OUTCEPTION_CORS_ORIGINS`** must include `https://outception.com`.
- **`OUTCEPTION_SECRET`** must be strong — the app refuses to boot in production
  with the dev default.
- **OAuth redirect URIs** in Google/GitHub/Apple consoles must point at
  `https://api.outception.com/...`.

## Monitoring

Two layers, both hitting the deep `/healthz` (it checks Postgres **and** Redis,
returning 503 if either is down):

1. **External monitor (primary).** Runs *off* the box, so it catches "the whole
   server is down."
   - **Built in:** the [`uptime.yml`](../.github/workflows/uptime.yml) GitHub
     Actions workflow probes `/healthz` every ~5 min from GitHub's runners and
     alerts + fails the run on a genuine outage. Just set the repo **variable**
     `HEALTHCHECK_URL` (and optional secret `ALERT_WEBHOOK_URL`). Free, no signup.
   - **Finer granularity:** for 1-minute checks + SMS/phone alerts, also point
     [UptimeRobot](https://uptimerobot.com) or [Better Stack](https://betterstack.com/uptime)
     at `https://api.<domain>/healthz` (create a free account → add an HTTP(s)
     monitor → keyword `"ok"`, interval 1 min → add your email/webhook).
2. **Host-side alert hook (`healthcheck-alert.sh` + timer).** Polls `/healthz`
   every 2 min and posts to a Slack/Discord webhook on **down** and **recovery**
   (once each, anti-flap). Catches app-level failures fast. Enable:
   ```bash
   # In .env.prod: OUTCEPTION_HEALTHCHECK_URL + OUTCEPTION_ALERT_WEBHOOK_URL
   #   (webhook: Slack "Incoming Webhooks" or Discord channel → Integrations → Webhooks)
   sudo systemctl enable --now outception-healthcheck.timer
   ```

Optionally set `OUTCEPTION_BACKUP_HEARTBEAT_URL` (e.g. a
[healthchecks.io](https://healthchecks.io) check) so a **silent backup failure**
also alerts you.

## Scaling notes

- The `worker` runs the scheduler **embedded** and must stay at **1 replica**
  (else cron jobs double-fire). To scale workers, remove
  `-f outception.worker.scheduler:start` from the worker command and add a
  separate single-replica scheduler service.
- Postgres/Redis run on the same host here. For real load, move Postgres to a
  managed/standalone host and add `OUTCEPTION_POSTGRES_READ_*` for a replica.

## Backups

Nightly PostgreSQL backups to Cloudflare R2 via `backup.sh` + a systemd timer —
host-side, so backups keep running even if GitHub or the app is down.

**Setup:**

1. Create a **private** R2 bucket and set `OUTCEPTION_S3_BACKUP_BUCKET_NAME` (plus
   the R2 endpoint + keys) in `.env.prod`.
2. `provision.sh` already installed the units. Enable the timer:
   ```bash
   sudo systemctl enable --now outception-backup.timer
   sudo /opt/outception/deploy/backup.sh        # run once to verify
   systemctl list-timers outception-backup.timer
   ```

Each run does `pg_dump -Fc` from the live `db` container and uploads
`postgres/outception-<timestamp>.dump`, keeping the most recent **30** (override
with `BACKUP_RETENTION`). Add an R2 lifecycle rule for belt-and-suspenders
off-box retention.

**Restore** (into a fresh/empty database):

```bash
cd /opt/outception/deploy
# fetch a dump from R2 (or copy one down), then:
cat outception-<timestamp>.dump | docker compose --env-file .env.prod \
  -f docker-compose.prod.yml exec -T db \
  pg_restore -U "$OUTCEPTION_POSTGRES_USER" -d "$OUTCEPTION_POSTGRES_DATABASE" --clean --if-exists
```
