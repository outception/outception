#!/usr/bin/env bash
# The app containers' env file: .env.prod without the keys only the host
# may hold, which are Caddy's DNS token, the backup's passphrase and bucket
# credentials (OUTCEPTION_BACKUP_*, digits included), and the alert and
# health hooks. The deploy runs this on every deploy. After editing
# .env.prod by hand, run it yourself and recreate the services:
#
#   ./app-env.sh
#   docker compose --env-file .env.prod -f docker-compose.prod.yml up -d
set -euo pipefail
cd "$(dirname "$0")"
[ -f .env.prod ] || { echo ".env.prod is missing" >&2; exit 1; }
umask 077
# grep -v exits 1 when it prints nothing; only a missing file is an error.
status=0
grep -v -E '^(CF_API_TOKEN|OUTCEPTION_BACKUP_[A-Z0-9_]+|OUTCEPTION_ALERT_WEBHOOK_URL|OUTCEPTION_HEALTHCHECK_URL)=' \
  .env.prod > .env.app.tmp || status=$?
[ "$status" -le 1 ] || { rm -f .env.app.tmp; exit "$status"; }
mv .env.app.tmp .env.app
chmod 600 .env.app
