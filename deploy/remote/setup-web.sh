#!/usr/bin/env bash
set -euo pipefail
D="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
R="$(cd "$D/../.." && pwd)"
source "$D/target.conf"
SSH=(-i "$DEPLOY_SSH_KEY" -o BatchMode=yes -o ConnectTimeout=15)
LOCAL_ENV="$R/apps/web/.env"
REMOTE_ENV="$DEPLOY_REMOTE_ROOT/apps/web/.env"
TEMP_ENV="$(mktemp)"
trap 'rm -f "$TEMP_ENV"' EXIT

echo "Preparando configuração remota da Web."
python3 "$R/deploy/core/env_tools.py" set "$LOCAL_ENV" "$TEMP_ENV" \
  "APP_HOST=127.0.0.1" \
  "APP_PORT=$DEPLOY_WEB_PORT" \
  "PUBLIC_REMOTE_API_URL=/api/mail" \
  "PUBLIC_ORBITAL_HOME_URL=$DEPLOY_ORBITAL_URL"
chmod 600 "$TEMP_ENV"
scp "${SSH[@]}" "$TEMP_ENV" "$DEPLOY_REMOTE_HOST:$REMOTE_ENV"
echo "Configuração remota da Web enviada."

echo "Instalando e preparando serviço da Web."
ssh "${SSH[@]}" "$DEPLOY_REMOTE_HOST" 'bash -s' -- \
  "$DEPLOY_REMOTE_ROOT" "$DEPLOY_WEB_SERVICE" "$DEPLOY_WEB_PORT" <<'REMOTE'
set -euo pipefail
ROOT="$1"
SERVICE="$2"
PORT="$3"
WEB="$ROOT/apps/web"
UI="$(dirname "$ROOT")/orbital-ui"
UNIT="$ROOT/deploy/remote/systemd/$SERVICE"
[[ -f "$UNIT" ]] || { echo "Unit da Web não encontrada: $UNIT" >&2; exit 1; }
sudo systemctl stop "$SERVICE" 2>/dev/null || true
if sudo fuser "$PORT/tcp" >/dev/null 2>&1; then
  echo "Liberando processo órfão da porta $PORT."
  sudo fuser -k "$PORT/tcp" >/dev/null
fi
sudo install -m 644 "$UNIT" "/etc/systemd/system/$SERVICE"
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE" >/dev/null
[[ -f "$UI/package.json" ]] || { echo "Dependência ausente: $UI/package.json" >&2; exit 1; }
cd "$WEB"
rm -rf .astro dist
npm ci
npm run check
npm run build
[[ -f dist/server/entry.mjs ]] || { echo "Build não gerou dist/server/entry.mjs." >&2; exit 1; }
echo "Serviço da Web instalado e preparado."
REMOTE
"$D/start-web.sh"
