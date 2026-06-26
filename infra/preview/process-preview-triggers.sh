#!/usr/bin/env bash
#
# Process preview infra triggers. Runs as root via systemd.
# The deploy user can only create trigger files — this script
# decides what privileged operations to perform.
#
set -euo pipefail

TRIGGER_DIR="/srv/preview-triggers"
PREVIEW_TOOLS_DIR="/srv/preview-tools"

while true; do
    found=false
    for trigger in "$TRIGGER_DIR"/*; do
        [[ -f "$trigger" ]] || continue
        found=true
        filename=$(basename "$trigger")

        case "$filename" in
            pr-*.deploy)
                PR_NUM="${filename#pr-}"
                PR_NUM="${PR_NUM%.deploy}"
                if [[ "$PR_NUM" =~ ^[0-9]+$ ]]; then
                    "$PREVIEW_TOOLS_DIR/regenerate-caddyfile.sh"
                    systemctl reload caddy
                    systemctl restart "outception-preview-backend@${PR_NUM}" || echo "[trigger] Failed to restart pr-${PR_NUM}"
                fi
                ;;
            pr-*.destroy)
                PR_NUM="${filename#pr-}"
                PR_NUM="${PR_NUM%.destroy}"
                if [[ "$PR_NUM" =~ ^[0-9]+$ ]]; then
                    systemctl stop "outception-preview-backend@${PR_NUM}" 2>/dev/null || true
                    systemctl stop "outception-preview-frontend@${PR_NUM}" 2>/dev/null || true
                    systemctl disable "outception-preview-backend@${PR_NUM}" 2>/dev/null || true
                    systemctl disable "outception-preview-frontend@${PR_NUM}" 2>/dev/null || true
                    "$PREVIEW_TOOLS_DIR/regenerate-caddyfile.sh"
                    systemctl reload caddy 2>/dev/null || true
                fi
                ;;
            pr-*.wake)
                PR_NUM="${filename#pr-}"
                PR_NUM="${PR_NUM%.wake}"
                if [[ "$PR_NUM" =~ ^[0-9]+$ ]]; then
                    if [[ ! -d "/srv/previews/pr-${PR_NUM}/server" ]]; then
                        echo "[trigger] No deployment for pr-${PR_NUM}, skipping wake"
                    elif ! systemctl is-active --quiet "outception-preview-backend@${PR_NUM}"; then
                        systemctl start "outception-preview-backend@${PR_NUM}" || echo "[trigger] Failed to start pr-${PR_NUM}"
                    fi
                fi
                ;;
        esac

        rm -f "$trigger"
    done
    "$found" || break
done
