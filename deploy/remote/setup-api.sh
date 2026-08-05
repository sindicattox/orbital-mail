#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_FILE="${DEPLOY_TARGET_FILE:-$SCRIPT_DIR/target.conf}"
source "$TARGET_FILE"
SSH=(-i "$DEPLOY_SSH_KEY" -o BatchMode=yes -o ConnectTimeout=15 -o ServerAliveInterval=30 -o ServerAliveCountMax=120)
ssh "${SSH[@]}" "$DEPLOY_REMOTE_HOST" 'bash -s' -- "$DEPLOY_REMOTE_ROOT" <<'REMOTE'
set -euo pipefail
ROOT_DIR="$1"; API_DIR="$ROOT_DIR/apps/api"
source "$ROOT_DIR/deploy/core/load-env.sh"; load_config_context "$API_DIR"
: "${API_SYSTEMD_SERVICE:?API_SYSTEMD_SERVICE ausente na configuração de produção}"
: "${APP_PORT:?APP_PORT ausente na configuração de produção}"
sudo systemctl stop "$API_SYSTEMD_SERVICE" 2>/dev/null || true
sudo fuser -k "${APP_PORT}/tcp" >/dev/null 2>&1 || true
cd "$API_DIR"; rm -rf .venv; python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
.venv/bin/python -c 'from core.settings import get_settings; get_settings()'
REMOTE
"$SCRIPT_DIR/start-api.sh"
