#!/usr/bin/env bash
set -euo pipefail
D="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$D/target.conf"
SSH=(-i "$DEPLOY_SSH_KEY" -o BatchMode=yes -o ConnectTimeout=15)
echo "Preparando Web remota."
ssh "${SSH[@]}" "$DEPLOY_REMOTE_HOST" 'bash -s' -- \
  "$DEPLOY_REMOTE_ROOT" "$DEPLOY_WEB_SERVICE" "$DEPLOY_WEB_PORT" <<'REMOTE'
set -euo pipefail
ROOT="$1"
SERVICE="$2"
PORT="$3"
WEB="$ROOT/apps/web"
UI="$(dirname "$ROOT")/orbital-ui"
[[ -f "$WEB/.env" ]] || { echo "Arquivo obrigatório não encontrado: $WEB/.env" >&2; exit 1; }
[[ -f "$UI/package.json" ]] || { echo "Dependência ausente: $UI/package.json" >&2; exit 1; }
sudo systemctl stop "$SERVICE" 2>/dev/null || true
sudo fuser -k "$PORT/tcp" >/dev/null 2>&1 || true
cd "$WEB"
rm -rf .astro dist
npm ci
npm run check
npm run build
[[ -f dist/server/entry.mjs ]] || { echo "Build não gerou dist/server/entry.mjs." >&2; exit 1; }
REMOTE
"$D/start-web.sh"
