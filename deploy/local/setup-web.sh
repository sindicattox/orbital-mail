#!/usr/bin/env bash
# cd /home/daniel/Code/orgs/orbital/orbital-mail
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WEB_DIR="$ROOT_DIR/apps/web"
echo "[orbital-mail] preparando Web em $WEB_DIR"
cd "$WEB_DIR"
npm install
[[ -f .env ]] || cp .env.example .env
echo "Web preparada com sucesso."
