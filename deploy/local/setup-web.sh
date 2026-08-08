#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
WEB_DIR="$ROOT_DIR/apps/web"
WEB_PORT=4106

echo "Parando Web local na porta $WEB_PORT..."
fuser -k "${WEB_PORT}/tcp" >/dev/null 2>&1 || true

echo "Preparando Web..."
cd "$WEB_DIR"
rm -rf .astro dist
npm ci

echo "Web preparada."
exec "$SCRIPT_DIR/start-web.sh"
