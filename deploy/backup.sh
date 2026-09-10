#!/usr/bin/env bash
#
# Nightly PostgreSQL backup -> Cloudflare R2.
#
# Dumps the live `db` container with pg_dump (compressed custom format) and
# uploads it to the R2 backup bucket, then prunes to the most recent N dumps.
# All credentials come from deploy/.env.prod. Runs from the host (see the
# systemd units in deploy/systemd/), so backups keep happening even if GitHub
# or the app is down. Uses only the running Postgres container + a throwaway
# aws-cli container - nothing extra to install on the host.
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
  [ -n "${!var}" ] || { echo "backup: ${name} is not set in .env.prod - configure R2 first." >&2; exit 1; }
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
    amazon/aws-cli@sha256:be7c8de0160a2e2269159bc2634c002c85b1a21d6322e2ad513b3f7f48325c99 --endpoint-url "$R2_ENDPOINT" "$@"
}

echo "[backup] pg_dump from db container"
# Use the container's own POSTGRES_USER/DB env; local connection needs no password.
compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$tmp/db.dump"
echo "[backup] dump size: $(du -h "$tmp/db.dump" | cut -f1)"

# Cost guard: never upload a dump larger than this. R2's free tier is 10 GB
# total; capping a SINGLE dump well under that keeps the whole retention set
# (RETENTION x this) inside free even in the worst case, so a runaway table
# can never quietly start costing money. Overridable via .env.prod; the
# nightly job aborts LOUDLY (dead-man's-switch never pings -> you get paged)
# rather than silently uploading a giant object.
MAX_MB="$(getenv OUTCEPTION_BACKUP_MAX_MB)"; MAX_MB="${MAX_MB:-9900}"
dump_mb=$(( $(stat -c %s "$tmp/db.dump") / 1024 / 1024 ))
if [ "$dump_mb" -gt "$MAX_MB" ]; then
  echo "[backup] ABORT: dump ${dump_mb}MB exceeds ${MAX_MB}MB cap - not uploading" >&2
  exit 1
fi

# Encrypt before upload when BACKUP_PASSPHRASE is set in .env.prod: the R2
# credentials live on this box, and an unencrypted bucket meant any leak of
# either exposed 30 days of full production dumps. Decrypt with:
#   openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -pass env:BACKUP_PASSPHRASE \
#     -in db.dump.enc -out db.dump
BACKUP_PASSPHRASE="$(getenv OUTCEPTION_BACKUP_PASSPHRASE)"
if [ -n "$BACKUP_PASSPHRASE" ]; then
  echo "[backup] encrypting dump"
  export BACKUP_PASSPHRASE
  openssl enc -aes-256-cbc -pbkdf2 -iter 200000 -salt \
    -pass env:BACKUP_PASSPHRASE -in "$tmp/db.dump" -out "$tmp/db.dump.enc"
  rm -f "$tmp/db.dump"
  mv "$tmp/db.dump.enc" "$tmp/db.dump"
  key="${key}.enc"
fi

echo "[backup] upload -> s3://${BUCKET}/${key}"
aws_r2 s3 cp /data/db.dump "s3://${BUCKET}/${key}"

echo "[backup] prune to last ${RETENTION}"
# Both suffixes, and || true: encrypted names never matched '.dump$', so
# encrypted backups grew unbounded (defeating the 30-day exposure bound the
# encryption promises), legacy plaintext dumps never aged out, and an
# encrypted-only bucket made grep exit 1 under set -e AFTER a good upload
# but BEFORE the heartbeat - a nightly false "backup failed" page.
aws_r2 s3 ls "s3://${BUCKET}/postgres/" \
  | awk '{print $4}' | { grep -E '\.dump(\.enc)?$' || true; } | sort \
  | head -n "-${RETENTION}" \
  | while read -r old; do
      [ -n "$old" ] && aws_r2 s3 rm "s3://${BUCKET}/postgres/${old}"
    done

# Self-verify the object we just wrote: re-download it, decrypt it, and let
# pg_restore parse the archive header. A backup that can't be restored is not
# a backup - proving it every night means the restore path can never rot
# unnoticed, and the operator never has to test by hand. A failure here fails
# the whole run (set -e), so the heartbeat below never pings and the monitor
# alerts. This is what makes the pipeline hands-off.
echo "[backup] verify: re-download + decrypt + validate"
verify_dir="$(mktemp -d)"
trap 'rm -rf "$tmp" "$verify_dir"' EXIT
aws_r2_to() {
  docker run --rm \
    -e AWS_ACCESS_KEY_ID="$R2_KEY" \
    -e AWS_SECRET_ACCESS_KEY="$R2_SECRET" \
    -e AWS_DEFAULT_REGION="$R2_REGION" \
    -v "$verify_dir:/v" \
    amazon/aws-cli@sha256:be7c8de0160a2e2269159bc2634c002c85b1a21d6322e2ad513b3f7f48325c99 \
    --endpoint-url "$R2_ENDPOINT" s3 cp "s3://${BUCKET}/${key}" /v/got
}
aws_r2_to
if [ -n "$BACKUP_PASSPHRASE" ]; then
  openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 \
    -pass env:BACKUP_PASSPHRASE -in "$verify_dir/got" -out "$verify_dir/plain"
else
  mv "$verify_dir/got" "$verify_dir/plain"
fi
compose exec -T db pg_restore -l < "$verify_dir/plain" >/dev/null
echo "[backup] verify OK: archive is restorable"

# Dead-man's-switch: ping a monitor (e.g. healthchecks.io) so a SILENT backup
# failure gets noticed - if this stop pinging, the monitor alerts you.
heartbeat="$(getenv OUTCEPTION_BACKUP_HEARTBEAT_URL)"
[ -n "$heartbeat" ] && curl -fsS -m 10 "$heartbeat" >/dev/null 2>&1 || true

echo "[backup] done: ${key}"
