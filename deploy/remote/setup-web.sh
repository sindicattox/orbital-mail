#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_FILE="${DEPLOY_TARGET_FILE:-$SCRIPT_DIR/target.conf}"
source "$TARGET_FILE"
SSH=(-i "$DEPLOY_SSH_KEY" -o BatchMode=yes -o ConnectTimeout=15 -o ServerAliveInterval=30 -o ServerAliveCountMax=120)
ssh "${SSH[@]}" "$DEPLOY_REMOTE_HOST" 'bash -s' -- "$DEPLOY_REMOTE_ROOT" <<'REMOTE'
set -euo pipefail
ROOT_DIR="$1"; WEB_DIR="$ROOT_DIR/apps/web"
source "$ROOT_DIR/deploy/core/load-env.sh"; load_config_context "$WEB_DIR"
: "${WEB_SYSTEMD_SERVICE:?WEB_SYSTEMD_SERVICE ausente na configuração de produção}"
: "${APP_PORT:?APP_PORT ausente na configuração de produção}"
sudo systemctl stop "$WEB_SYSTEMD_SERVICE" 2>/dev/null || true
sudo fuser -k "${APP_PORT}/tcp" >/dev/null 2>&1 || true
cd "$WEB_DIR"; rm -rf .astro dist; npm ci; npm run build; test -s dist/server/entry.mjs
REMOTE
"$SCRIPT_DIR/start-web.sh"
