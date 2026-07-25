#!/usr/bin/env bash
# cd /home/daniel/Code/orgs/orbital/orbital-mail
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
[[ -x "$API_DIR/.venv/bin/uvicorn" ]] || { echo "API não preparada. Execute ./deploy/local/setup-api.sh" >&2; exit 1; }
cd "$API_DIR"
exec .venv/bin/uvicorn main:app --host 0.0.0.0 --port 8102 --reload
