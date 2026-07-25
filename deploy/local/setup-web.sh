#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WEB_DIR="$ROOT_DIR/apps/web"
[[ -f "$WEB_DIR/.env" ]] || cp "$WEB_DIR/.env.example" "$WEB_DIR/.env"
echo "[orbital-mail] preparando Web em $WEB_DIR"
cd "$WEB_DIR"
rm -rf .astro dist
npm install
echo "Web preparada com sucesso."
