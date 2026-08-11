#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_FILE="${DEPLOY_TARGET_FILE:-$SCRIPT_DIR/target.conf}"

[[ -f "$TARGET_FILE" ]] || { echo "Destino não encontrado: $TARGET_FILE" >&2; exit 1; }
# shellcheck source=/dev/null
source "$TARGET_FILE"

SSH_KEY="${DEPLOY_SSH_KEY:?Defina DEPLOY_SSH_KEY em $TARGET_FILE}"
REMOTE_HOST="${DEPLOY_REMOTE_HOST:?Defina DEPLOY_REMOTE_HOST em $TARGET_FILE}"
REMOTE_ROOT="${DEPLOY_REMOTE_ROOT:?Defina DEPLOY_REMOTE_ROOT em $TARGET_FILE}"
SSH=(-i "$SSH_KEY" -o BatchMode=yes -o ConnectTimeout=15 -o ServerAliveInterval=30 -o ServerAliveCountMax=120)

echo "Preparando mail worker remoto..."
ssh "${SSH[@]}" "$REMOTE_HOST" 'bash -s' -- "$REMOTE_ROOT" <<'REMOTE'
set -euo pipefail

ROOT_DIR="$1"
API_DIR="$ROOT_DIR/apps/api"
APP_CONFIG="$API_DIR/config/production/app.env"
[[ -f "$APP_CONFIG" ]] || { echo "Configuração da API não encontrada: $APP_CONFIG" >&2; exit 1; }
API_PORT="$(sed -n 's/^APP_PORT=//p' "$APP_CONFIG")"
API_SERVICE="$(sed -n 's/^API_SYSTEMD_SERVICE=//p' "$APP_CONFIG")"
WORKER_SERVICE="$(sed -n 's/^MAIL_WORKER_SYSTEMD_SERVICE=//p' "$APP_CONFIG")"

[[ "$API_PORT" =~ ^[0-9]+$ ]] && ((API_PORT >= 1 && API_PORT <= 65535)) || { echo "APP_PORT inválido." >&2; exit 1; }
[[ "$API_SERVICE" =~ ^[A-Za-z0-9_.@:-]+\.service$ ]] || { echo "API_SYSTEMD_SERVICE inválido." >&2; exit 1; }
[[ "$WORKER_SERVICE" =~ ^[A-Za-z0-9_.@:-]+\.service$ ]] || { echo "MAIL_WORKER_SYSTEMD_SERVICE inválido." >&2; exit 1; }

OLD_API_PID="$(systemctl show "$API_SERVICE" -p MainPID --value 2>/dev/null || true)"
OLD_API_PID="${OLD_API_PID:-0}"
sudo systemctl stop "$WORKER_SERVICE" 2>/dev/null || true

API_READY=false
for _ in {1..300}; do
    CURRENT_API_PID="$(systemctl show "$API_SERVICE" -p MainPID --value 2>/dev/null || true)"
    CURRENT_API_PID="${CURRENT_API_PID:-0}"
    if [[ "$CURRENT_API_PID" != "0" && "$CURRENT_API_PID" != "$OLD_API_PID" ]] \
        && curl -fsS --max-time 2 "http://127.0.0.1:${API_PORT}/api/health/worker" >/dev/null 2>&1; then
        API_READY=true
        break
    fi
    sleep 1
done

[[ "$API_READY" == true ]] || {
    echo "Erro: API remota não ficou pronta para iniciar o mail worker." >&2
    exit 1
}

"$ROOT_DIR/deploy/remote/systemd/install.sh" "$ROOT_DIR" "$WORKER_SERVICE"
sudo systemctl restart "$WORKER_SERVICE"
for _ in {1..30}; do
    systemctl is-active --quiet "$WORKER_SERVICE" || {
        echo "Erro: $WORKER_SERVICE não está ativo." >&2
        sudo systemctl status "$WORKER_SERVICE" --no-pager -l >&2 || true
        sudo journalctl -u "$WORKER_SERVICE" -n 40 --no-pager >&2 || true
        exit 1
    }
    if curl -fsS --max-time 2 "http://127.0.0.1:${API_PORT}/api/health/worker" >/dev/null 2>&1; then
        exit 0
    fi
    sleep 1
done

echo "Erro: mail worker remoto não ficou pronto." >&2
exit 1
REMOTE

echo "Mail worker remoto iniciado."
