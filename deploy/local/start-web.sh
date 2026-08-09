#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
WEB_DIR="$ROOT_DIR/apps/web"

[[ -d "$WEB_DIR/node_modules" ]] || {
    echo "Web não preparada. Execute setup-web.sh." >&2
    exit 1
}

ln -sfn local "$WEB_DIR/config/runtime"
cd "$WEB_DIR"
echo "Iniciando Web local..."
exec npm run dev
