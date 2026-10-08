#!/usr/bin/env bash
# Carry the git-excluded files the swap needs from the live tree's backup
# into the rebuilt tree, without overwriting anything the rebuilt tree has.
#
#   scripts/swap-carry-over.sh <live backup> <rebuilt tree> [--commit]
#
# Without --commit it only prints what it would copy. The list is fixed on
# purpose: env files for removed features (payments, object storage,
# analytics) stay behind, and the rebuilt tree keeps its own server/.env.
set -euo pipefail

from="${1:?the live backup tree}"
to="${2:?the rebuilt tree}"
mode="${3:-dry-run}"

carry=(
  "server/.jwks.json"                  # the development signing key set
  "clients/apps/app/.env"              # the app's build-time env
  "clients/apps/app/credentials.json"  # the store signing credentials
  "clients/apps/app/credentials"       # the keystores those point at
)

for path in "${carry[@]}"; do
  if [ ! -e "$from/$path" ]; then
    echo "absent in the backup, nothing to carry: $path"
  elif [ -e "$to/$path" ]; then
    echo "kept, the rebuilt tree has its own: $path"
  elif [ "$mode" = "--commit" ]; then
    cp -a "$from/$path" "$to/$path"
    echo "carried: $path"
  else
    echo "would carry: $path"
  fi
done
