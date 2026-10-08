<!-- doc-covers: deploy server/.env.prod.example .github/workflows/deploy.yml -->
<!-- doc-verified: d5090b2 -->

# Deployment

One host runs the whole stack with Docker Compose: PostgreSQL, Redis, the
API, one worker with the scheduler embedded, the web server, and the edge
proxy for TLS. The host runbook (provisioning, DNS, first boot, backups) is
`deploy/README.md`. This page is the configuration contract.

## The env contract

`server/.env.prod.example` lists every `OUTCEPTION_*` name the server
reads; `scripts/check_env_vars.py` fails CI when it drifts from the
settings. `deploy/.env.prod.example` is the operator's file: the
compose-level keys first, then the contract verbatim, and CI checks that it
carries every contract name. Copy it to `deploy/.env.prod` on the host and
fill it; the filled file never enters the tree.

The settings that break the product when wrong:

| Setting                                                                | Why                                                                                                                                                                                                                                                                                    |
| ---------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `OUTCEPTION_ENV=production`                                            | Turns the production guards on; the app refuses to boot while `OUTCEPTION_SECRET` is the development default.                                                                                                                                                                          |
| `OUTCEPTION_SECRET`                                                    | Keys every token hash. Strong, unique, never rotated casually.                                                                                                                                                                                                                         |
| `OUTCEPTION_LOCAL_JWKS`, `OUTCEPTION_LOCAL_JWK_KID`                    | The signing keypair, a file mounted read-only from `deploy/secrets/jwks.json`, and the key id it was generated with. The deploy mints one with that key id when the file is missing; the app refuses to boot on the public development key set. It carries over unchanged at the swap. |
| `OUTCEPTION_ENCRYPTION_LOCAL_KEY`                                      | Wraps the stored secrets (sessions, sign-in states, linked accounts) when there is no KMS key. The deploy mints it once into the env file; keep that file, since the secrets cannot be read without it.                                                                                |
| `OUTCEPTION_SUMMARY_MODEL`                                             | The paid summary lane's model id. The tree never names a model; the deploy fills it from the repository variable `SUMMARY_MODEL`, and without it the paid lane stays off while the free fleet carries on.                                                                              |
| `OUTCEPTION_POSTGRES_*`, `OUTCEPTION_REDIS_*`                          | The database and the broker, on the internal network.                                                                                                                                                                                                                                  |
| `OUTCEPTION_BASE_URL`, `OUTCEPTION_FRONTEND_BASE_URL`                  | The public API and web URLs, used in links and redirects.                                                                                                                                                                                                                              |
| `OUTCEPTION_ALLOWED_HOSTS`, `OUTCEPTION_CORS_ORIGINS`                  | The API and web hosts; the web origin that may send credentials.                                                                                                                                                                                                                       |
| `OUTCEPTION_TRUSTED_PROXY_IPS`, `OUTCEPTION_TRUSTED_CLIENT_IP_HEADERS` | The edge tier the API trusts for the client address; set to the internal network, never the public internet.                                                                                                                                                                           |
| `OUTCEPTION_ACCOUNTS_ENABLED`                                          | On since the first week; readers never need an account to read, and the deploy sets it true.                                                                                                                                                                                           |
| `OUTCEPTION_ADMIN_EMAILS`                                              | Who may open the Products of the day review page, comma-separated; an account flagged admin in the database counts too. The web asks the API.                                                                                                                                         |
| `OUTCEPTION_MEDIA_DIR`                                                 | Product logos for the daily card, on the `media_data` volume.                                                                                                                                                                                                                          |
| `OUTCEPTION_EMAIL_*`                                                   | SMTP for the one-time codes and the submitter's reply; the deploy fills it from repository secrets.                                                                                                                                                                                    |
| `LLM_*`, `DECISION_CHAIN_*`, `ENGINE_URL`                              | The governor's lanes, caps and chains; every key stays in the provider modules and the env, nowhere else.                                                                                                                                                                              |

Every typed setting in the examples carries its default, so a `.env.prod`
copied from `deploy/.env.prod.example` and filled with the secrets alone
boots; a `KEY=` line means the default, never an empty string.
`python -m scripts.env_examples --check` keeps the examples that way and
`tests/test_env_examples.py` loads each one into the settings.

Migrations run in the one-shot `migrate` service before the API and the
worker start.

The `engine` service sits under the `engine` compose profile and stays off
until a checkpoint is on the `engine_models` volume; `docs/ENGINE.md` is the
runbook. The swap from the live tree is `docs/SWAP.md`.

## Web

`NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_FRONTEND_BASE_URL`,
`NEXT_PUBLIC_ENVIRONMENT`, `NEXT_PUBLIC_SENTRY_DSN` and
`NEXT_PUBLIC_COUNTER_TOKEN` (the visit counter's public project key) are
baked into the bundle at build time by the deploy workflow from repository
variables, and `NEXT_PUBLIC_BUILD_SHA` from the commit, for the client
version header. The web server reads the API over
the internal network through `OUTCEPTION_API_URL`.

## App

`EXPO_PUBLIC_OUTCEPTION_SERVER_URL` and `EXPO_PUBLIC_OUTCEPTION_WEB_URL`
per build profile in `clients/apps/app/eas.json`; the OAuth client id the
shipped binary uses must keep its id across the swap.

The visit counter takes its public id at build time from the repository
variable `NEXT_PUBLIC_POSTHOG_TOKEN` (the web image's `NEXT_PUBLIC_COUNTER_TOKEN` build arg); an
empty variable leaves it out of the bundle. It runs cookieless, see
`docs/VISION.md` rule 2. The founder's reach chart reads the counter back
through its query API: set `OUTCEPTION_POSTHOG_API_KEY` (a personal key
with query read) and `OUTCEPTION_POSTHOG_PROJECT_ID` in `.env.prod` on the
host (`OUTCEPTION_POSTHOG_HOST` defaults to the European instance). The worker
syncs views per day, page and country into `site_visits` at seven past
every hour; unset, the sync logs once and the chart stays empty.

## Deploys and the boundary

Every push to `main` builds both images and pushes them to the registry
with the workflow's own token: each package grants the repository Write
under its Actions access. The host pulls with `GHCR_PAT`, which needs
`read:packages` only, so a host compromise cannot push an image. The
deploy job runs in the protected `production` environment, which requires a named
reviewer: that is the publication boundary, and
`server/tests/test_publication_boundary.py` keeps it in place, for the
deploy and for the four `ops-*` workflows that reach the host. The deploy
checks the host out at the exact commit, pulls, brings the stack up,
health-gates `/healthz` and a CORS preflight, and rolls back the running
services on failure. Nothing in CI submits to a store.

Every SSH step in the workflows checks the host key against the repository
variable `SSH_HOST_FINGERPRINT`: the `SHA256:` form that `ssh-keygen -lf`
prints for the host's ECDSA key, the type the deploy client negotiates
first (`ssh-keyscan -t ecdsa <host> | ssh-keygen -lf -`). The workflows
refuse to run while the variable is empty, and a stale one refuses to
connect, so after a host rebuild set it before the next deploy.

The host's firewall opens 22 to everyone and 80 and 443 only to the edge's
published ranges, so a caller who learns the origin address still comes
through the edge. Because Caddy's ports are published through Docker, whose
forwarding rules accept traffic before the host firewall sees it, the
script (`deploy/firewall.sh`) keeps the ranges in an address set checked
from Docker's `DOCKER-USER` chain as well as in the host rules. Root runs a
root-owned copy, `/usr/local/sbin/outception-firewall`, installed by
provisioning. The `outception-firewall` service runs it at every boot
before Docker starts (the address sets and the forwarding rule live in
memory), from the last good list kept in `/var/lib/outception-firewall`
when the network is not up yet, and retries a minute later if it fails; the
timer runs it again a minute after boot, online, and weekly. A download
that fails, or brings back a blank or short list, never empties the sets:
the saved list is applied instead. Every run converges, so running it
again is always safe. After a deploy that changes the script or its units,
read the change, then reinstall the copy:

```bash
git -C /opt/outception log -1 -p -- deploy/firewall.sh deploy/systemd
install -o root -g root -m 755 /opt/outception/deploy/firewall.sh /usr/local/sbin/outception-firewall
install -m 644 /opt/outception/deploy/systemd/outception-firewall.* /etc/systemd/system/
systemctl daemon-reload
systemctl enable outception-firewall.service
systemctl enable --now outception-firewall.timer
/usr/local/sbin/outception-firewall
```

Inside the API image the code is owned by
root and read-only to the app user; `/data/media` (the logo volume) is the
one path it writes, and a volume created before the image owned that path
needs one ownership pass on the host:

```bash
cd /opt/outception/deploy
docker compose --env-file .env.prod -f docker-compose.prod.yml \
  run --rm --no-deps --user 0:0 --entrypoint sh api -c 'chown 1001:1001 /data/media'
```

The host keeps one `.env.prod` for compose, Caddy and the backup. Each
deploy derives `.env.app` from it without the host-only keys (the DNS token
Caddy uses for certificates, everything under `OUTCEPTION_BACKUP_*`, which
is the backup's passphrase and its own bucket credentials, and the alert
and health-check hooks); that is the file the API, the worker and the
migration load, so the app never holds a secret it does not use. The web
server reads only the few values compose interpolates for it. Give the
backup its own bucket key under `OUTCEPTION_BACKUP_S3_ACCESS_KEY_ID`,
`OUTCEPTION_BACKUP_S3_SECRET_ACCESS_KEY` and `OUTCEPTION_BACKUP_S3_BUCKET`;
until those are set the backup falls back to the app's. Caddy sets the edge headers (HSTS, `nosniff`, the referrer policy)
and strips every client-address header before it forwards; the API keys its
limits on the socket peer, which uvicorn takes from Caddy's pinned
`X-Forwarded-For` and nothing else.

The first deploy after the swap also carries the host over from the live
tree, once, before the stack comes up: it keeps a copy of the env file as
`.env.prod.pre-swap`, creates the `outception_rebuild` database next to
the live one and points the app at it, carries the signing key over under
`OUTCEPTION_LOCAL_JWKS` and `OUTCEPTION_LOCAL_JWK_KID` with the live key
id. After the health gate it runs the live data
import (`scripts.import_live_data --source-database <live db> --commit`)
and leaves a marker so it never runs twice. The live database is never
written, so the rollback in `SWAP.md` is the old stack against it.

## Verification before a swap

```bash
cp deploy/.env.prod.example deploy/.env.prod   # on a staging host, then fill
docker compose --env-file deploy/.env.prod -f deploy/docker-compose.prod.yml config --quiet
docker build --target production -f server/Dockerfile server
docker build -f deploy/web.Dockerfile clients
cd server && uv run python -m scripts.check_env_vars
```
