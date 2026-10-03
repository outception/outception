#!/bin/bash
# Startup script for Outception API and Worker services in development mode
# This script handles dependency installation, email template building,
# database migrations, and service startup with hot-reloading.

set -euo pipefail

cd /app/server

echo "=== Outception Backend Startup ==="
echo "Service: ${1:-api}"

# Retry a command a few times with linear backoff. Container startup pulls git
# dependencies over the network (e.g. the dramatiq fork), and Docker's embedded
# DNS can flap transiently — a single failure shouldn't kill the whole boot.
retry() {
    local -r max="${RETRY_MAX:-3}"
    local n=1
    until "$@"; do
        if (( n >= max )); then
            echo "ERROR: '$*' failed after ${max} attempts" >&2
            return 1
        fi
        echo "'$*' failed (attempt ${n}/${max}); retrying in $(( n * 5 ))s..." >&2
        sleep $(( n * 5 ))
        n=$(( n + 1 ))
    done
}

# Reconcile the virtualenv against the lockfile on every boot. This is a fast
# no-op when already in sync, and — unlike an mtime check — it also repairs a
# venv whose interpreter no longer matches .python-version (e.g. after a base
# image bump), which would otherwise fail lazily in a later `uv run`.
echo "Syncing Python dependencies..."
retry uv sync --frozen

# Build email templates for this architecture (API only to avoid race conditions)
# The binary must be built for the container's architecture (Linux), not host (macOS)
ARCH=$(uname -m)
EMAIL_MARKER="emails/bin/.built-${ARCH}"
if [[ "${1:-api}" == "api" ]] && [[ ! -f "$EMAIL_MARKER" ]]; then
    echo "Building email templates for ${ARCH}..."
    cd emails
    export CI=true
    # Clean previous builds (may be from different architecture)
    rm -rf dist
    rm -f bin/react-email-pkg bin/.built-* 2>/dev/null || true
    # Point pnpm at the mounted store volume for faster installs via env var,
    # so we don't mutate the bind-mounted (and git-tracked) pnpm-workspace.yaml.
    export pnpm_config_store_dir=/root/.local/share/pnpm/store
    # Install dependencies (uses shared pnpm store for speed)
    pnpm install --frozen-lockfile
    # Build: tsup compiles TypeScript, pkg creates standalone binary
    pnpm exec tsup
    pnpm exec pkg package.json
    # Mark as built for this architecture
    touch "bin/.built-${ARCH}"
    cd ..
    echo "Email templates built for ${ARCH}"
elif [[ "${1:-api}" == "worker" ]] && [[ ! -f "$EMAIL_MARKER" ]]; then
    echo "Waiting for API to build email templates..."
    while [[ ! -f "$EMAIL_MARKER" ]]; do
        sleep 2
    done
    echo "Email templates ready"
else
    echo "Email templates already built for ${ARCH}"
fi

# Generate JWKS if not present
if [[ ! -f ".jwks.json" ]]; then
    echo "Generating development JWKS..."
    uv run python -c "
from authlib.jose import JsonWebKey, KeySet
options = {'kid': 'outception_dev', 'use': 'sig'}
key = JsonWebKey.generate_key('RSA', 2048, options, is_private=True)
keyset = KeySet(keys=[key])
with open('.jwks.json', 'w') as f:
    f.write(keyset.as_json(is_private=True))
"
    echo "JWKS generated"
else
    echo "JWKS already exists"
fi

# Wait for database to be ready
echo "Waiting for database..."
max_attempts=30
attempt=0
while ! pg_isready -h "$OUTCEPTION_POSTGRES_HOST" -p "$OUTCEPTION_POSTGRES_PORT" -U "$OUTCEPTION_POSTGRES_USER" -q; do
    attempt=$((attempt + 1))
    if [[ $attempt -ge $max_attempts ]]; then
        echo "ERROR: Database not ready after $max_attempts attempts"
        exit 1
    fi
    echo "Database not ready, waiting... (attempt $attempt/$max_attempts)"
    sleep 2
done
echo "Database is ready"

# Bootstrap the per-instance database on the shared infrastructure
# (api only). Skipped when the marker file from a previous successful boot is
# still present; the marker lives in the api_venv volume so `dev docker
# cleanup` (which removes that volume) forces a re-bootstrap.
BOOTSTRAP_MARKER="/app/server/.venv/.bootstrap-${OUTCEPTION_POSTGRES_DATABASE}.done"
if [[ "${1:-api}" == "api" && ! -f "$BOOTSTRAP_MARKER" ]]; then
    READ_USER="${OUTCEPTION_POSTGRES_READ_USER:-outception_read}"
    echo "Bootstrapping per-instance DB '$OUTCEPTION_POSTGRES_DATABASE'..."
    # createdb ignores existing DBs (returns nonzero, suppressed); GRANTs are
    # idempotent. Read-only USER itself is created once by
    # server/init-readonly-user.sql on first postgres init.
    PGPASSWORD="$OUTCEPTION_POSTGRES_PWD" createdb -h "$OUTCEPTION_POSTGRES_HOST" \
        -p "$OUTCEPTION_POSTGRES_PORT" -U "$OUTCEPTION_POSTGRES_USER" \
        -O "$OUTCEPTION_POSTGRES_USER" "$OUTCEPTION_POSTGRES_DATABASE" 2>/dev/null || true
    PGPASSWORD="$OUTCEPTION_POSTGRES_PWD" psql -h "$OUTCEPTION_POSTGRES_HOST" \
        -p "$OUTCEPTION_POSTGRES_PORT" -U "$OUTCEPTION_POSTGRES_USER" \
        -d "$OUTCEPTION_POSTGRES_DATABASE" -v ON_ERROR_STOP=1 <<SQL >/dev/null
GRANT CONNECT ON DATABASE "$OUTCEPTION_POSTGRES_DATABASE" TO $READ_USER;
GRANT USAGE ON SCHEMA public TO $READ_USER;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO $READ_USER;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO $READ_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO $READ_USER;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE ON SEQUENCES TO $READ_USER;
SQL
    touch "$BOOTSTRAP_MARKER"
    echo "Bootstrap complete: $OUTCEPTION_POSTGRES_DATABASE"
fi

# Run database migrations (only for API, not worker to avoid race conditions)
if [[ "${1:-api}" == "api" ]]; then
    echo "Running database migrations..."
    uv run alembic upgrade head
    echo "Migrations complete"
else
    echo "Skipping migrations (handled by API service)"
    # Wait a bit for API to run migrations first
    sleep 10
fi

# Start the requested service
case "${1:-api}" in
    api)
        echo "Starting API server with hot-reload..."
        echo "API will be available at http://localhost:8000"
        exec uv run uvicorn outception.app:app \
            --reload \
            --reload-dir outception \
            --host 0.0.0.0 \
            --port 8000 \
            --workers 1
        ;;
    worker)
        echo "Starting background worker with hot-reload..."
        exec uv run dramatiq \
            -p 1 \
            -t 1 \
            --queues high_priority medium_priority low_priority news_pipeline \
            --watch outception \
            -f outception.worker.scheduler:start \
            outception.worker.run
        ;;
    shell)
        echo "Starting shell..."
        exec /bin/bash
        ;;
    *)
        echo "Unknown service: $1"
        echo "Available services: api, worker, shell"
        exit 1
        ;;
esac
