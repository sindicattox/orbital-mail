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
SSH=(-i "$SSH_KEY" -o BatchMode=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=120)

echo "Iniciando Web remota..."
ssh "${SSH[@]}" "$REMOTE_HOST" 'bash -s' <<'REMOTE'
set -euo pipefail

WEB_SERVICE="orbital-mail-web.service"

sudo systemctl restart "$WEB_SERVICE"
systemctl is-active --quiet "$WEB_SERVICE"
for _ in {1..30}; do
    if curl -fsS --max-time 2 http://127.0.0.1:4106/orbital-mail/ >/dev/null 2>&1; then
        exit 0
    fi

    sleep 1
done

echo "Erro: Web não respondeu em http://127.0.0.1:4106/orbital-mail/." >&2
exit 1
REMOTE

echo "Web remota iniciada."
