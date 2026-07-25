#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
API_ENV="$API_DIR/.env"
[[ -f "$API_ENV" ]] || cp "$API_DIR/.env.example" "$API_ENV"
echo "[orbital-mail] preparando API em $API_DIR"
rm -rf "$API_DIR/.venv"
python3 -m venv "$API_DIR/.venv"
"$API_DIR/.venv/bin/python" -m pip install --upgrade pip
"$API_DIR/.venv/bin/pip" install -r "$API_DIR/requirements.txt"
echo "API preparada com sucesso."
