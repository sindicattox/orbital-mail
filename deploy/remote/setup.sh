#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
TARGET_FILE="${DEPLOY_TARGET_FILE:-$SCRIPT_DIR/target.conf}"
source "$TARGET_FILE"
SSH=(-i "$DEPLOY_SSH_KEY" -o BatchMode=yes -o ConnectTimeout=15 -o ServerAliveInterval=30 -o ServerAliveCountMax=120)
[[ -f "$DEPLOY_SSH_KEY" ]] || { echo "Chave SSH não encontrada: $DEPLOY_SSH_KEY" >&2; exit 1; }
command -v rsync >/dev/null || { echo "rsync não encontrado localmente." >&2; exit 1; }
echo "Enviando código para $DEPLOY_REMOTE_HOST:$DEPLOY_REMOTE_ROOT..."
ssh "${SSH[@]}" "$DEPLOY_REMOTE_HOST" "mkdir -p $(printf '%q' "$DEPLOY_REMOTE_ROOT")"
rsync -az --delete --itemize-changes -e "ssh ${SSH[*]}" \
  --exclude='.git/' --exclude='.idea/' --exclude='.vscode/' --exclude='.pytest_cache/' \
  --exclude='*.pyc' --exclude='__pycache__/' --exclude='*.remove' \
  --exclude='apps/api/.env' --exclude='apps/web/.env' --exclude='apps/api/.venv/' --exclude='apps/api/logs/' \
  --exclude='apps/web/node_modules/' --exclude='apps/web/.astro/' --exclude='apps/web/dist/' \
  "$ROOT_DIR/" "$DEPLOY_REMOTE_HOST:$DEPLOY_REMOTE_ROOT/"
echo "Código enviado."
"$SCRIPT_DIR/setup-api.sh"
"$SCRIPT_DIR/setup-web.sh"
echo "Deploy remoto concluído."
