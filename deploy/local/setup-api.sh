#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
API_PORT=8106

echo "Parando API local na porta $API_PORT..."
fuser -k "${API_PORT}/tcp" >/dev/null 2>&1 || true

echo "Preparando API..."
rm -rf "$API_DIR/.venv"
python3 -m venv "$API_DIR/.venv"
"$API_DIR/.venv/bin/pip" install -r "$API_DIR/requirements.txt"

echo "API preparada."
exec "$SCRIPT_DIR/start-api.sh"
