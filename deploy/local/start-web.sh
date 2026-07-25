#!/usr/bin/env bash
# cd /home/daniel/Code/orgs/orbital/orbital-mail
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WEB_DIR="$ROOT_DIR/apps/web"
[[ -d "$WEB_DIR/node_modules" ]] || { echo "Web não preparada. Execute ./deploy/local/setup-web.sh" >&2; exit 1; }
cd "$WEB_DIR"
exec npm run dev
