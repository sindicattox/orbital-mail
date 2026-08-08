#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_FILE="${DEPLOY_TARGET_FILE:-$SCRIPT_DIR/target.conf}"

[[ -f "$TARGET_FILE" ]] || {
    echo "Destino não encontrado: $TARGET_FILE" >&2
    exit 1
}

# shellcheck source=/dev/null
source "$TARGET_FILE"

SSH_KEY="${DEPLOY_SSH_KEY:?Defina DEPLOY_SSH_KEY em $TARGET_FILE}"
REMOTE_HOST="${DEPLOY_REMOTE_HOST:?Defina DEPLOY_REMOTE_HOST em $TARGET_FILE}"
REMOTE_ROOT="${DEPLOY_REMOTE_ROOT:?Defina DEPLOY_REMOTE_ROOT em $TARGET_FILE}"
SSH=(-i "$SSH_KEY" -o BatchMode=yes -o ConnectTimeout=15 -o ServerAliveInterval=30 -o ServerAliveCountMax=120)

echo "Parando e preparando API remota..."
ssh "${SSH[@]}" "$REMOTE_HOST" 'bash -s' -- "$REMOTE_ROOT" <<'REMOTE'
set -euo pipefail

ROOT_DIR="$1"
API_DIR="$ROOT_DIR/apps/api"
API_PORT=8106
API_SERVICE="orbital-mail-api.service"

sudo systemctl stop "$API_SERVICE" 2>/dev/null || true
sudo fuser -k "${API_PORT}/tcp" >/dev/null 2>&1 || true

cd "$API_DIR"
rm -rf .venv
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
REMOTE

echo "API remota preparada."
exec "$SCRIPT_DIR/start-api.sh"
