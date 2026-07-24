#!/usr/bin/env bash
#
# Nightly PostgreSQL backup -> Cloudflare R2.
#
# Dumps the live `db` container with pg_dump (compressed custom format) and
# uploads it to the R2 backup bucket, then prunes to the most recent N dumps.
# All credentials come from deploy/.env.prod. Runs from the host (see the
# systemd units in deploy/systemd/), so backups keep happening even if GitHub
# or the app is down. Uses only the running Postgres container + a throwaway
# aws-cli container — nothing extra to install on the host.
#
# Manual run:  DEPLOY_DIR=/opt/outception/deploy ./backup.sh
#
set -euo pipefail

DEPLOY_DIR="${DEPLOY_DIR:-$(cd "$(dirname "$0")" && pwd)}"
cd "$DEPLOY_DIR"

# Pull only the R2 values we need out of .env.prod WITHOUT sourcing it (the file
# holds JSON-ish values like CORS_ORIGINS=[...] that would break shell parsing).
getenv() {
  local v
  v="$(grep -E "^${1}=" .env.prod | tail -1 | sed -E "s/^${1}=//")" || true
  v="${v%\"}"; v="${v#\"}"   # strip surrounding double quotes if present
  printf '%s' "$v"
}

R2_ENDPOINT="$(getenv OUTCEPTION_S3_ENDPOINT_URL)"
R2_KEY="$(getenv OUTCEPTION_AWS_ACCESS_KEY_ID)"
R2_SECRET="$(getenv OUTCEPTION_AWS_SECRET_ACCESS_KEY)"
R2_REGION="$(getenv OUTCEPTION_AWS_REGION)"; R2_REGION="${R2_REGION:-auto}"
BUCKET="$(getenv OUTCEPTION_S3_BACKUP_BUCKET_NAME)"
RETENTION="${BACKUP_RETENTION:-30}"   # keep this many most-recent dumps in R2

for pair in "R2_ENDPOINT:OUTCEPTION_S3_ENDPOINT_URL" "R2_KEY:OUTCEPTION_AWS_ACCESS_KEY_ID" \
            "R2_SECRET:OUTCEPTION_AWS_SECRET_ACCESS_KEY" "BUCKET:OUTCEPTION_S3_BACKUP_BUCKET_NAME"; do
  var="${pair%%:*}"; name="${pair##*:}"
  [ -n "${!var}" ] || { echo "backup: ${name} is not set in .env.prod — configure R2 first." >&2; exit 1; }
done

stamp="$(date -u +%Y%m%d-%H%M%S)"
key="postgres/outception-${stamp}.dump"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT

compose() { docker compose --env-file .env.prod -f docker-compose.prod.yml "$@"; }
aws_r2() {
  docker run --rm \
    -e AWS_ACCESS_KEY_ID="$R2_KEY" \
    -e AWS_SECRET_ACCESS_KEY="$R2_SECRET" \
    -e AWS_DEFAULT_REGION="$R2_REGION" \
    -v "$tmp:/data" \
    amazon/aws-cli --endpoint-url "$R2_ENDPOINT" "$@"
}

echo "[backup] pg_dump from db container"
# Use the container's own POSTGRES_USER/DB env; local connection needs no password.
compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$tmp/db.dump"
echo "[backup] dump size: $(du -h "$tmp/db.dump" | cut -f1)"

echo "[backup] upload -> s3://${BUCKET}/${key}"
aws_r2 s3 cp /data/db.dump "s3://${BUCKET}/${key}"

echo "[backup] prune to last ${RETENTION}"
aws_r2 s3 ls "s3://${BUCKET}/postgres/" \
  | awk '{print $4}' | grep -E '\.dump$' | sort | head -n "-${RETENTION}" \
  | while read -r old; do
      [ -n "$old" ] && aws_r2 s3 rm "s3://${BUCKET}/postgres/${old}"
    done

# Dead-man's-switch: ping a monitor (e.g. healthchecks.io) so a SILENT backup
# failure gets noticed — if this stop pinging, the monitor alerts you.
heartbeat="$(getenv OUTCEPTION_BACKUP_HEARTBEAT_URL)"
[ -n "$heartbeat" ] && curl -fsS -m 10 "$heartbeat" >/dev/null 2>&1 || true

echo "[backup] done: ${key}"
