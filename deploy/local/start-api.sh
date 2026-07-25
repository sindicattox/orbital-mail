#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
API_ENV="$API_DIR/.env"
[[ -f "$API_ENV" ]] || { echo "Arquivo obrigatório não encontrado: $API_ENV" >&2; exit 1; }
set -a
source "$API_ENV"
set +a
: "${APP_HOST:?Defina APP_HOST em $API_ENV}"
: "${APP_PORT:?Defina APP_PORT em $API_ENV}"
[[ -x "$API_DIR/.venv/bin/uvicorn" ]] || { echo "API não preparada. Execute ./deploy/local/setup-api.sh" >&2; exit 1; }
cd "$API_DIR"
echo "API: http://127.0.0.1:${APP_PORT}"
exec .venv/bin/uvicorn main:app --host "$APP_HOST" --port "$APP_PORT" --reload
