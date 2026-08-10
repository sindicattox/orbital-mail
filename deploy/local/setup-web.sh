#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
WEB_DIR="$ROOT_DIR/apps/web"
APP_CONFIG="$WEB_DIR/config/local/app.env"
[[ -f "$APP_CONFIG" ]] || { echo "Configuração da Web não encontrada: $APP_CONFIG" >&2; exit 1; }
WEB_PORT="$(sed -n 's/^APP_PORT=//p' "$APP_CONFIG")"
[[ "$WEB_PORT" =~ ^[0-9]+$ ]] && ((WEB_PORT >= 1 && WEB_PORT <= 65535)) || { echo "APP_PORT inválido." >&2; exit 1; }

echo "Parando Web local na porta $WEB_PORT..."
fuser -k "${WEB_PORT}/tcp" >/dev/null 2>&1 || true

echo "Preparando Web..."
cd "$WEB_DIR"
rm -rf .astro dist
npm ci

echo "Web preparada."
exec "$SCRIPT_DIR/start-web.sh"
