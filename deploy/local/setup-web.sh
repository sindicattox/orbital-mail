#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
WEB_DIR="$ROOT_DIR/apps/web"
source "$ROOT_DIR/deploy/core/load-env.sh"
load_config_context "$WEB_DIR"
: "${APP_PORT:?APP_PORT ausente em apps/web/config/local/app.env}"
command -v fuser >/dev/null || { echo "fuser não encontrado." >&2; exit 1; }
echo "Parando Web local na porta $APP_PORT..."
fuser -k "${APP_PORT}/tcp" >/dev/null 2>&1 || true
cd "$WEB_DIR"
rm -rf .astro dist
npm ci
echo "Web preparada. Iniciando..."
exec "$SCRIPT_DIR/start-web.sh"
