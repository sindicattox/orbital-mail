#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
PYTHON="$API_DIR/.venv/bin/python"
UVICORN="$API_DIR/.venv/bin/uvicorn"

[[ -x "$PYTHON" && -x "$UVICORN" ]] || {
    echo "API não preparada. Execute setup-api.sh." >&2
    exit 1
}

cd "$API_DIR"
"$PYTHON" -c 'from core.settings import get_settings; get_settings()'
read -r API_HOST API_PORT < <("$PYTHON" -c 'from core.settings import get_settings; s=get_settings(); print(s.app_host, s.app_port)')

echo "Iniciando API local em ${API_HOST}:${API_PORT}..."
exec "$UVICORN" main:app --reload --host "$API_HOST" --port "$API_PORT"
