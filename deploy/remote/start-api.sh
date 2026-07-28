#!/usr/bin/env bash
set -euo pipefail
D="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$D/target.conf"
SSH=(-i "$DEPLOY_SSH_KEY" -o BatchMode=yes -o ConnectTimeout=15)
echo "Iniciando e validando API na porta $DEPLOY_API_PORT."
ssh "${SSH[@]}" "$DEPLOY_REMOTE_HOST" 'bash -s' -- \
  "$DEPLOY_API_SERVICE" "$DEPLOY_API_PORT" <<'REMOTE'
set -euo pipefail
SERVICE="$1"
PORT="$2"
sudo systemctl restart "$SERVICE"
for PATHNAME in /api/health /api/health/db; do
  URL="http://127.0.0.1:$PORT$PATHNAME"
  for _ in {1..20}; do
    curl -fsS --max-time 5 "$URL" >/dev/null 2>&1 && break
    sleep 2
  done
  curl -fsS --max-time 5 "$URL" >/dev/null
  echo "Disponível: $URL"
done
REMOTE
