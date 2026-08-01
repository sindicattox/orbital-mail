#!/usr/bin/env bash
set -euo pipefail
D="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
R="$(cd "$D/../.." && pwd)"
source "$D/target.conf"
SSH=(-i "$DEPLOY_SSH_KEY" -o BatchMode=yes -o ConnectTimeout=15)
LOCAL_ENV="$R/apps/api/.env"
REMOTE_ENV="$DEPLOY_REMOTE_ROOT/apps/api/.env"
TEMP_ENV="$(mktemp)"
trap 'rm -f "$TEMP_ENV"' EXIT

echo "Preparando configuração remota da API."
python3 "$R/deploy/core/env_tools.py" set "$LOCAL_ENV" "$TEMP_ENV" \
  "APP_ENV=production" \
  "APP_HOST=127.0.0.1" \
  "APP_PORT=$DEPLOY_API_PORT" \
  "APP_CORS_ORIGINS=$DEPLOY_PUBLIC_URL,$DEPLOY_ORBITAL_URL" \
  "AUTH_MODE=remote" \
  "AUTH_CONTEXT_URL=http://127.0.0.1:8001/auth/context" \
  "EMAIL_UPLOAD_DIR=/home/ubuntu/storage/tenants/{tenant}/media/email_campaign" \
  "EMAIL_UPLOAD_PUBLIC_URL=$DEPLOY_PUBLIC_URL/api/mail/uploads"
chmod 600 "$TEMP_ENV"
scp "${SSH[@]}" "$TEMP_ENV" "$DEPLOY_REMOTE_HOST:$REMOTE_ENV"
echo "Configuração remota da API enviada."

echo "Instalando e preparando serviço da API."
ssh "${SSH[@]}" "$DEPLOY_REMOTE_HOST" 'bash -s' -- \
  "$DEPLOY_REMOTE_ROOT" "$DEPLOY_API_SERVICE" "$DEPLOY_API_PORT" <<'REMOTE'
set -euo pipefail
ROOT="$1"
SERVICE="$2"
PORT="$3"
API="$ROOT/apps/api"
UNIT="$ROOT/deploy/remote/systemd/$SERVICE"
[[ -f "$UNIT" ]] || { echo "Unit da API não encontrada: $UNIT" >&2; exit 1; }
sudo systemctl stop "$SERVICE" 2>/dev/null || true
if sudo fuser "$PORT/tcp" >/dev/null 2>&1; then
  echo "Liberando processo órfão da porta $PORT."
  sudo fuser -k "$PORT/tcp" >/dev/null
fi
sudo install -m 644 "$UNIT" "/etc/systemd/system/$SERVICE"
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE" >/dev/null
cd "$API"
rm -rf .venv
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
.venv/bin/python - <<'PY'
from core.settings import get_settings
settings = get_settings()
print(f'Configuração validada: {settings.app_service} / {settings.app_env}')
print(f'Contexto de autenticação: {settings.auth_context_url}')
PY
echo "Serviço da API instalado e preparado."
REMOTE
"$D/start-api.sh"
