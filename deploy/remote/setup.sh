#!/usr/bin/env bash
set -euo pipefail
D="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
R="$(cd "$D/../.." && pwd)"
source "$D/target.conf"
SSH=(-i "$DEPLOY_SSH_KEY" -o BatchMode=yes -o ConnectTimeout=15)
[[ -f "$DEPLOY_SSH_KEY" ]] || { echo "Chave ausente: $DEPLOY_SSH_KEY" >&2; exit 1; }
command -v rsync >/dev/null || { echo "rsync não encontrado." >&2; exit 1; }
echo "Sincronizando código com $DEPLOY_REMOTE_HOST:$DEPLOY_REMOTE_ROOT."
ssh "${SSH[@]}" "$DEPLOY_REMOTE_HOST" "mkdir -p '$DEPLOY_REMOTE_ROOT'"
rsync -az --delete --itemize-changes -e "ssh ${SSH[*]}" \
  --exclude='.git/' --exclude='.idea/' --exclude='.pytest_cache/' --exclude='*[REMOVER]*' \
  --exclude='apps/api/.env' --exclude='apps/api/.venv/' --exclude='apps/api/.emails_para_teste' \
  --exclude='apps/web/.env' --exclude='apps/web/node_modules/' --exclude='apps/web/.astro/' --exclude='apps/web/dist/' \
  --exclude='__pycache__/' --exclude='*.pyc' "$R/" "$DEPLOY_REMOTE_HOST:$DEPLOY_REMOTE_ROOT/"
ssh "${SSH[@]}" "$DEPLOY_REMOTE_HOST" "chmod 755 '$DEPLOY_REMOTE_ROOT'"
echo "Código remoto sincronizado."
"$D/setup-api.sh"
"$D/setup-web.sh"
echo "Deploy remoto concluído."
