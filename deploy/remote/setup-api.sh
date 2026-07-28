#!/usr/bin/env bash
set -euo pipefail
D="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$D/target.conf"
SSH=(-i "$DEPLOY_SSH_KEY" -o BatchMode=yes -o ConnectTimeout=15)
echo "Preparando API remota."
ssh "${SSH[@]}" "$DEPLOY_REMOTE_HOST" 'bash -s' -- \
  "$DEPLOY_REMOTE_ROOT" "$DEPLOY_API_SERVICE" "$DEPLOY_API_PORT" <<'REMOTE'
set -euo pipefail
ROOT="$1"
SERVICE="$2"
PORT="$3"
API="$ROOT/apps/api"
[[ -f "$API/.env" ]] || { echo "Arquivo obrigatório não encontrado: $API/.env" >&2; exit 1; }
sudo systemctl stop "$SERVICE" 2>/dev/null || true
sudo fuser -k "$PORT/tcp" >/dev/null 2>&1 || true
cd "$API"
rm -rf .venv
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
.venv/bin/python - <<'PY'
from core.settings import get_settings
settings = get_settings()
if settings.app_env.strip().lower() not in {'production', 'prod', 'remote'}:
    raise SystemExit('APP_ENV deve ser production no servidor.')
print(f'Configuração validada: {settings.app_service} / {settings.app_env}')
PY
REMOTE
"$D/start-api.sh"
