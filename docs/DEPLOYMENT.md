<!-- doc-covers: deploy server/.env.prod.example .github/workflows/deploy.yml -->
<!-- doc-verified: 2579d8a -->

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

| Setting | Why |
| --- | --- |
| `OUTCEPTION_ENV=production` | Turns the production guards on; the app refuses to boot while `OUTCEPTION_SECRET` is the development default. |
| `OUTCEPTION_SECRET` | Keys every token hash. Strong, unique, never rotated casually. |
| `OUTCEPTION_LOCAL_JWKS`, `OUTCEPTION_LOCAL_JWK_KID` | The signing keypair, a file mounted read-only from `deploy/secrets/jwks.json`, and the key id it was generated with. The deploy mints one with that key id when the file is missing; the app refuses to boot on the public development key set. It carries over unchanged at the swap. |
| `OUTCEPTION_POSTGRES_*`, `OUTCEPTION_REDIS_*` | The database and the broker, on the internal network. |
| `OUTCEPTION_BASE_URL`, `OUTCEPTION_FRONTEND_BASE_URL` | The public API and web URLs, used in links and redirects. |
| `OUTCEPTION_ALLOWED_HOSTS`, `OUTCEPTION_CORS_ORIGINS` | The API and web hosts; the web origin that may send credentials. |
| `OUTCEPTION_TRUSTED_PROXY_IPS`, `OUTCEPTION_TRUSTED_CLIENT_IP_HEADERS` | The edge tier the API trusts for the client address; set to the internal network, never the public internet. |
| `OUTCEPTION_ACCOUNTS_ENABLED` | Off in production until accounts are switched on; readers never need one. |
| `OUTCEPTION_ADMIN_EMAILS`, `NEXT_PUBLIC_ADMIN_EMAILS` | Who may open the Products of the day review page; the two must agree. |
| `OUTCEPTION_MEDIA_DIR` | Product logos for the daily card, on the `media_data` volume. |
| `OUTCEPTION_EMAIL_*` | SMTP for the one-time codes and the submitter's reply; the deploy fills it from repository secrets. |
| `OUTCEPTION_WEB_PUSH_VAPID_PUBLIC_KEY`, `OUTCEPTION_WEB_PUSH_VAPID_PRIVATE_KEY`, `OUTCEPTION_WEB_PUSH_SUBJECT` | The morning briefing push on the web. Generate the pair once with `vapid --gen` from the server env and keep it; the subject is a `mailto:` address. Unset, the notify switch is hidden. |
| `LLM_*`, `DECISION_CHAIN_*`, `ENGINE_URL` | The governor's lanes, caps and chains; every key stays in the provider modules and the env, nowhere else. |

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
`NEXT_PUBLIC_ADMIN_EMAILS` are baked into the bundle at build time by the
deploy workflow from repository variables, and `NEXT_PUBLIC_BUILD_SHA` from
the commit, for the client version header. The web server reads the API over
the internal network through `OUTCEPTION_API_URL`.

## App

`EXPO_PUBLIC_OUTCEPTION_SERVER_URL` and `EXPO_PUBLIC_OUTCEPTION_WEB_URL`
per build profile in `clients/apps/app/eas.json`; the OAuth client id the
shipped binary uses must keep its id across the swap.

## Deploys and the boundary

Every push to `main` builds both images and pushes them to the registry.
The deploy job runs in the protected `production` environment, which
requires a named reviewer: that is the publication boundary, and
`server/tests/test_publication_boundary.py` keeps it in place. The deploy
checks the host out at the exact commit, pulls, brings the stack up,
health-gates `/healthz` and a CORS preflight, and rolls back the running
services on failure. Nothing in CI submits to a store.

## Verification before a swap

```bash
cp deploy/.env.prod.example deploy/.env.prod   # on a staging host, then fill
docker compose --env-file deploy/.env.prod -f deploy/docker-compose.prod.yml config --quiet
docker build --target production -f server/Dockerfile server
docker build -f deploy/web.Dockerfile clients
cd server && uv run python -m scripts.check_env_vars
```
