#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
source "$ROOT_DIR/deploy/core/load-env.sh"
load_config_context "$API_DIR"
: "${APP_HOST:?APP_HOST ausente em apps/api/config/local/app.env}"
: "${APP_PORT:?APP_PORT ausente em apps/api/config/local/app.env}"
[[ -x "$API_DIR/.venv/bin/uvicorn" ]] || { echo "API não preparada. Execute ./deploy/local/setup-api.sh" >&2; exit 1; }
cd "$API_DIR"
.venv/bin/python -c 'from core.settings import get_settings; get_settings()'
echo "API: http://127.0.0.1:${APP_PORT}"
exec .venv/bin/uvicorn main:app --host "$APP_HOST" --port "$APP_PORT" --reload
