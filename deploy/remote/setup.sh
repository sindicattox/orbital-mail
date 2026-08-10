#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
TARGET_FILE="${DEPLOY_TARGET_FILE:-$SCRIPT_DIR/target.conf}"

[[ -f "$TARGET_FILE" ]] || { echo "Destino não encontrado: $TARGET_FILE" >&2; exit 1; }
# shellcheck source=/dev/null
source "$TARGET_FILE"

SSH_KEY="${DEPLOY_SSH_KEY:?Defina DEPLOY_SSH_KEY em $TARGET_FILE}"
REMOTE_HOST="${DEPLOY_REMOTE_HOST:?Defina DEPLOY_REMOTE_HOST em $TARGET_FILE}"
REMOTE_ROOT="${DEPLOY_REMOTE_ROOT:?Defina DEPLOY_REMOTE_ROOT em $TARGET_FILE}"
SSH=(-i "$SSH_KEY" -o BatchMode=yes -o ConnectTimeout=15 -o ServerAliveInterval=30 -o ServerAliveCountMax=120)

[[ -f "$SSH_KEY" ]] || { echo "Chave SSH não encontrada: $SSH_KEY" >&2; exit 1; }
command -v rsync >/dev/null || { echo "rsync não encontrado localmente." >&2; exit 1; }

echo "Enviando código para $REMOTE_HOST:$REMOTE_ROOT..."
ssh "${SSH[@]}" "$REMOTE_HOST" "mkdir -p $(printf '%q' "$REMOTE_ROOT")"
rsync -az --delete --itemize-changes \
    -e "ssh ${SSH[*]}" \
    --exclude='.git/' \
    --exclude='.idea/' \
    --exclude='.vscode/' \
    --exclude='.pytest_cache/' \
    --exclude='*.pyc' \
    --exclude='__pycache__/' \
    --exclude='*.remover' \
    --exclude='*.external' \
    --exclude='apps/api/.venv/' \
    --exclude='apps/api/logs/' \
    --exclude='apps/api/.emails_para_teste' \
    --exclude='apps/api/config/wallet/' \
    --exclude='apps/web/node_modules/' \
    --exclude='apps/web/.astro/' \
    --exclude='apps/web/dist/' \
    "$ROOT_DIR/" "$REMOTE_HOST:$REMOTE_ROOT/"

echo "Código enviado."
"$SCRIPT_DIR/setup-api.sh"
"$SCRIPT_DIR/setup-web.sh"
echo "Deploy remoto concluído."
