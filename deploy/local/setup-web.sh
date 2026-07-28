#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WEB_DIR="$ROOT_DIR/apps/web"
UI_DIR="$(dirname "$ROOT_DIR")/orbital-ui"
[[ -f "$WEB_DIR/.env" ]] || cp "$WEB_DIR/.env.example" "$WEB_DIR/.env"
[[ -f "$UI_DIR/package.json" ]] || { echo "Dependência ausente: $UI_DIR/package.json" >&2; exit 1; }
echo "[orbital-mail] preparando Web em $WEB_DIR"
cd "$WEB_DIR"
rm -rf .astro dist
npm ci
echo "Web preparada com sucesso."
