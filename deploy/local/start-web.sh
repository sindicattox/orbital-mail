#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
WEB_DIR="$ROOT_DIR/apps/web"
source "$ROOT_DIR/deploy/core/load-env.sh"
load_config_context "$WEB_DIR"
: "${APP_HOST:?APP_HOST ausente em apps/web/config/local/app.env}"
: "${APP_PORT:?APP_PORT ausente em apps/web/config/local/app.env}"
[[ -d "$WEB_DIR/node_modules" ]] || { echo "Web não preparada. Execute ./deploy/local/setup-web.sh" >&2; exit 1; }
cd "$WEB_DIR"
echo "Web: http://127.0.0.1:${APP_PORT}"
exec npm run dev -- --host "$APP_HOST" --port "$APP_PORT" --strictPort
