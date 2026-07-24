#!/usr/bin/env bash
#
# Poll the public /healthz and alert a webhook (Slack / Discord compatible) when
# the app goes DOWN, and again when it RECOVERS — once each, no spam. Host-side
# complement to an external uptime monitor: it catches app-level failures (a dead
# container, DB/Redis down) even while the box itself is up. For "the whole box
# is offline" you still want an EXTERNAL monitor (see deploy/README.md).
#
# Config from deploy/.env.prod (or the environment):
#   OUTCEPTION_HEALTHCHECK_URL     e.g. https://api.outception.com/healthz
#   OUTCEPTION_ALERT_WEBHOOK_URL   Slack / Discord incoming-webhook URL (optional)
#
set -euo pipefail

DEPLOY_DIR="${DEPLOY_DIR:-$(cd "$(dirname "$0")" && pwd)}"
cd "$DEPLOY_DIR"

getenv() {
  local v
  v="$(grep -E "^${1}=" .env.prod 2>/dev/null | tail -1 | sed -E "s/^${1}=//")" || true
  v="${v%\"}"; v="${v#\"}"
  printf '%s' "$v"
}

URL="${HEALTHCHECK_URL:-$(getenv OUTCEPTION_HEALTHCHECK_URL)}"
HOOK="${ALERT_WEBHOOK_URL:-$(getenv OUTCEPTION_ALERT_WEBHOOK_URL)}"
THRESHOLD="${HEALTH_FAIL_THRESHOLD:-2}"   # consecutive fails before alerting (anti-flap)
STATE="${HEALTH_STATE_FILE:-/var/tmp/outception-health.state}"

[ -n "$URL" ] || { echo "healthcheck: OUTCEPTION_HEALTHCHECK_URL not set" >&2; exit 1; }

notify() {
  echo "$1"
  [ -n "$HOOK" ] || return 0
  # "text" = Slack, "content" = Discord; each ignores the other's key.
  curl -fsS -m 10 -H 'Content-Type: application/json' \
    -d "{\"text\":\"$1\",\"content\":\"$1\"}" "$HOOK" >/dev/null 2>&1 || true
}

prev="UP"; fails=0
[ -f "$STATE" ] && read -r prev fails < "$STATE" 2>/dev/null || true
fails="${fails:-0}"

tmp="$(mktemp)"; trap 'rm -f "$tmp"' EXIT
code="$(curl -fsS -m 10 -o "$tmp" -w '%{http_code}' "$URL" 2>/dev/null || echo 000)"

if [ "$code" = "200" ] && grep -q '"ok"' "$tmp"; then
  [ "$prev" = "DOWN" ] && notify "✅ Outception RECOVERED — ${URL} is healthy again"
  echo "UP 0" > "$STATE"
else
  fails=$((fails + 1))
  if [ "$fails" -ge "$THRESHOLD" ] && [ "$prev" != "DOWN" ]; then
    notify "🔴 Outception DOWN — ${URL} failing (HTTP ${code}) for ${fails} checks"
    echo "DOWN ${fails}" > "$STATE"
  else
    echo "${prev} ${fails}" > "$STATE"
  fi
fi
