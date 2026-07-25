#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WEB_DIR="$ROOT_DIR/apps/web"
WEB_ENV="$WEB_DIR/.env"
[[ -f "$WEB_ENV" ]] || { echo "Arquivo obrigatório não encontrado: $WEB_ENV" >&2; exit 1; }
set -a
source "$WEB_ENV"
set +a
: "${APP_HOST:?Defina APP_HOST em $WEB_ENV}"
: "${APP_PORT:?Defina APP_PORT em $WEB_ENV}"
[[ -d "$WEB_DIR/node_modules" ]] || { echo "Web não preparada. Execute ./deploy/local/setup-web.sh" >&2; exit 1; }
cd "$WEB_DIR"
echo "Web: http://127.0.0.1:${APP_PORT}"
exec npm run dev -- --host "$APP_HOST" --port "$APP_PORT" --strictPort
