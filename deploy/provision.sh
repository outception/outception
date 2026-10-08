#!/usr/bin/env bash
#
# One-time Hetzner host bootstrap for Outception.
#
# Run as root on a fresh Ubuntu 24.04 box:
#
#   DEPLOY_SSH_PUBKEY="ssh-ed25519 AAAA... ci-deploy" bash provision.sh
#
# Installs Docker, creates the unprivileged `deploy` user the CI workflow
# SSHes in as, clones the repo, and opens the firewall for HTTP/S. Idempotent -
# safe to re-run. It does NOT touch secrets: .env.prod and the JWKS keypair are
# generated interactively afterwards (see the printed next steps).
#
set -euo pipefail

DEPLOY_USER="${DEPLOY_USER:-deploy}"
APP_DIR="${APP_DIR:-/opt/outception}"
REPO_URL="${REPO_URL:-https://github.com/outception/outception.git}"
HARDEN_SSH="${HARDEN_SSH:-1}"   # default ON: password auth + root login off (set 0 to opt out)

log() { printf '\n==> %s\n' "$*"; }

[ "$(id -u)" -eq 0 ] || { echo "Run as root (sudo)." >&2; exit 1; }

log "Base packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y ca-certificates curl git ufw

log "Docker + compose plugin"
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi
systemctl enable --now docker

log "Deploy user: ${DEPLOY_USER}"
if ! id "${DEPLOY_USER}" >/dev/null 2>&1; then
  adduser --disabled-password --gecos "" "${DEPLOY_USER}"
fi
usermod -aG docker "${DEPLOY_USER}"

if [ -n "${DEPLOY_SSH_PUBKEY:-}" ]; then
  log "Installing CI deploy key for ${DEPLOY_USER}"
  install -d -m 700 -o "${DEPLOY_USER}" -g "${DEPLOY_USER}" "/home/${DEPLOY_USER}/.ssh"
  keys="/home/${DEPLOY_USER}/.ssh/authorized_keys"
  touch "${keys}"
  grep -qF "${DEPLOY_SSH_PUBKEY}" "${keys}" || echo "${DEPLOY_SSH_PUBKEY}" >>"${keys}"
  chown "${DEPLOY_USER}:${DEPLOY_USER}" "${keys}"
  chmod 600 "${keys}"
else
  echo "   (no DEPLOY_SSH_PUBKEY given - add the CI public key to"
  echo "    /home/${DEPLOY_USER}/.ssh/authorized_keys yourself before enabling CI)"
fi

log "Repo at ${APP_DIR}"
if [ ! -d "${APP_DIR}/.git" ]; then
  git clone "${REPO_URL}" "${APP_DIR}"
fi
git config --system --add safe.directory "${APP_DIR}"
chown -R "${DEPLOY_USER}:${DEPLOY_USER}" "${APP_DIR}"
install -d -m 700 -o "${DEPLOY_USER}" -g "${DEPLOY_USER}" "${APP_DIR}/deploy/secrets"

log "Firewall (SSH + HTTP/S)"
# SSH open; 80 and 443 only from the edge's ranges. Root runs a root-owned
# copy of the script (the checkout belongs to the deploy user and every
# deploy rewrites it): the service at every boot, before Docker, and the
# timer a minute after boot and weekly. Re-run these lines after a deploy
# that changes the script or its units.
install -o root -g root -m 755 "${APP_DIR}/deploy/firewall.sh" /usr/local/sbin/outception-firewall
install -m 644 "${APP_DIR}"/deploy/systemd/outception-firewall.service \
  "${APP_DIR}"/deploy/systemd/outception-firewall.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable outception-firewall.service
systemctl enable --now outception-firewall.timer
/usr/local/sbin/outception-firewall

log "Install backup + health-monitor timers (enable them after .env.prod is filled)"
if [ -d "${APP_DIR}/deploy/systemd" ]; then
  install -m 644 "${APP_DIR}"/deploy/systemd/*.service /etc/systemd/system/
  install -m 644 "${APP_DIR}"/deploy/systemd/*.timer /etc/systemd/system/
  systemctl daemon-reload
  echo "   installed - after configuring .env.prod, enable with:"
  echo "     systemctl enable --now outception-backup.timer outception-healthcheck.timer"
fi

if [ "${HARDEN_SSH}" = "1" ]; then
  log "Hardening SSH (key-only, no root password login)"
  # A drop-in named to sort first: sshd takes the first value it sees, and
  # Ubuntu includes sshd_config.d before the main file, so a cloud-init
  # drop-in cannot quietly keep passwords on.
  mkdir -p /etc/ssh/sshd_config.d
  printf 'PasswordAuthentication no\nPermitRootLogin prohibit-password\n' > /etc/ssh/sshd_config.d/00-outception.conf
  sshd -t && (systemctl reload ssh 2>/dev/null || systemctl reload sshd 2>/dev/null || true)
  echo "   SSH now key-only - make sure ${DEPLOY_USER}'s key works before you log out."
fi

cat <<EOF

Bootstrap complete. Finish setup as the ${DEPLOY_USER} user:

  sudo -iu ${DEPLOY_USER}
  cd ${APP_DIR}/deploy
  cp .env.prod.example .env.prod
  \$EDITOR .env.prod                 # fill EVERY blank (domains, DB pwd, gateway, R2, CF token)

  # OUTCEPTION_SECRET (prod refuses to boot on the dev default):
  openssl rand -hex 32

  # OUTCEPTION_LOCAL_JWKS - RS256 keypair mounted at /run/secrets/jwks.json,
  # generated with a key id of your own; set OUTCEPTION_LOCAL_JWK_KID to it:
  ( cd ${APP_DIR}/server && uv run python -m outception.kit.jwk outception_prod > ../deploy/secrets/jwks.json )
  #   ...or generate it once on your laptop and scp it to
  #   ${APP_DIR}/deploy/secrets/jwks.json

  # First boot (builds locally the first time; CI pulls prebuilt images after).
  # The apps read .env.app, the copy of .env.prod without host-only keys;
  # rerun ./app-env.sh after any later hand edit of .env.prod:
  ./app-env.sh
  docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
  curl -fsS https://api.<your-domain>/healthz     # expect {"status":"ok"}

  # Backups (set OUTCEPTION_BACKUP_S3_ACCESS_KEY_ID, _SECRET_ACCESS_KEY and
  # _BUCKET, the backup's own bucket key) + health alerts
  # (set OUTCEPTION_HEALTHCHECK_URL + OUTCEPTION_ALERT_WEBHOOK_URL) in .env.prod:
  sudo systemctl enable --now outception-backup.timer outception-healthcheck.timer
  sudo /opt/outception/deploy/backup.sh           # optional: run one now to verify

Then wire up CI (deploy on push to main):
  GitHub repo Secrets:   SSH_HOST, SSH_USER=${DEPLOY_USER}, SSH_PRIVATE_KEY, GHCR_PAT (read:packages)
  GitHub repo Variables: NEXT_PUBLIC_API_URL, NEXT_PUBLIC_FRONTEND_BASE_URL,
                         DEPLOY_PATH=${APP_DIR}/deploy
EOF
