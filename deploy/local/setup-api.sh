#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
source "$ROOT_DIR/deploy/core/load-env.sh"
load_config_context "$API_DIR"
: "${APP_PORT:?APP_PORT ausente em apps/api/config/local/app.env}"
command -v fuser >/dev/null || { echo "fuser não encontrado." >&2; exit 1; }
echo "Parando API local na porta $APP_PORT..."
fuser -k "${APP_PORT}/tcp" >/dev/null 2>&1 || true
echo "Preparando API em $API_DIR..."
rm -rf "$API_DIR/.venv"
python3 -m venv "$API_DIR/.venv"
"$API_DIR/.venv/bin/python" -m pip install --upgrade pip
"$API_DIR/.venv/bin/pip" install -r "$API_DIR/requirements.txt"
echo "API preparada. Iniciando..."
exec "$SCRIPT_DIR/start-api.sh"
