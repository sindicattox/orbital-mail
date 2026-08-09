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
SSH=(-i "$SSH_KEY" -o BatchMode=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=120)

echo "Iniciando API remota..."
ssh "${SSH[@]}" "$REMOTE_HOST" 'bash -s' -- "$REMOTE_ROOT" <<'REMOTE'
set -euo pipefail

ROOT_DIR="$1"
API_DIR="$ROOT_DIR/apps/api"
API_SERVICE="orbital-mail-api.service"

ln -sfn production "$API_DIR/config/runtime"

sudo systemctl restart "$API_SERVICE"
systemctl is-active --quiet "$API_SERVICE"
for _ in {1..30}; do
    if curl -fsS --max-time 2 http://127.0.0.1:8106/api/health >/dev/null 2>&1; then
        exit 0
    fi

    sleep 1
done

echo "Erro: API não respondeu em http://127.0.0.1:8106/api/health." >&2
exit 1
REMOTE

echo "API remota iniciada."
