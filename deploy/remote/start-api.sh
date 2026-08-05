#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; source "${DEPLOY_TARGET_FILE:-$SCRIPT_DIR/target.conf}"
SSH=(-i "$DEPLOY_SSH_KEY" -o BatchMode=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=120)
ssh "${SSH[@]}" "$DEPLOY_REMOTE_HOST" 'bash -s' -- "$DEPLOY_REMOTE_ROOT" <<'REMOTE'
set -euo pipefail
ROOT_DIR="$1"; source "$ROOT_DIR/deploy/core/load-env.sh"; load_config_context "$ROOT_DIR/apps/api"
: "${API_SYSTEMD_SERVICE:?}"; : "${APP_PORT:?}"
sudo systemctl restart "$API_SYSTEMD_SERVICE"
for path in /api/health /api/health/db; do
  for _ in {1..20}; do curl -fsS --max-time 5 "http://127.0.0.1:${APP_PORT}${path}" >/dev/null 2>&1 && break; sleep 2; done
  curl -fsS --max-time 5 "http://127.0.0.1:${APP_PORT}${path}" >/dev/null
  echo "Disponível: http://127.0.0.1:${APP_PORT}${path}"
done
REMOTE
