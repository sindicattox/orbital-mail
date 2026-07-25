#!/usr/bin/env bash
# cd /home/daniel/Code/orgs/orbital/orbital-mail
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
echo "[orbital-mail] preparando API em $API_DIR"
python3 -m venv "$API_DIR/.venv"
"$API_DIR/.venv/bin/python" -m pip install --upgrade pip
"$API_DIR/.venv/bin/pip" install -r "$API_DIR/requirements.txt"
[[ -f "$API_DIR/.env" ]] || cp "$API_DIR/.env.example" "$API_DIR/.env"
echo "API preparada com sucesso."
