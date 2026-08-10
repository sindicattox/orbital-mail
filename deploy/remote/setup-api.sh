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
APP_CONFIG="$API_DIR/config/production/app.env"
[[ -f "$APP_CONFIG" ]] || { echo "Configuração da API não encontrada: $APP_CONFIG" >&2; exit 1; }
API_PORT="$(sed -n 's/^APP_PORT=//p' "$APP_CONFIG")"
API_SERVICE="$(sed -n 's/^API_SYSTEMD_SERVICE=//p' "$APP_CONFIG")"

[[ "$API_PORT" =~ ^[0-9]+$ ]] && ((API_PORT >= 1 && API_PORT <= 65535)) || { echo "APP_PORT inválido." >&2; exit 1; }
[[ "$API_SERVICE" =~ ^[A-Za-z0-9_.@:-]+\.service$ ]] || { echo "API_SYSTEMD_SERVICE inválido." >&2; exit 1; }

sudo systemctl stop "$API_SERVICE" 2>/dev/null || true
sudo fuser -k "${API_PORT}/tcp" >/dev/null 2>&1 || true

cd "$API_DIR"
rm -rf .venv
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
"$ROOT_DIR/deploy/remote/systemd/install.sh" "$ROOT_DIR" "$API_SERVICE"
REMOTE

echo "API remota preparada."
exec "$SCRIPT_DIR/start-api.sh"
