#!/usr/bin/env bash
# cd /home/daniel/Code/orgs/orbital/orbital-mail
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
echo "Iniciando orbital-mail local. Pressione Ctrl+C para encerrar."
echo "Site: http://localhost:4104/"
echo "API: http://127.0.0.1:8104"
echo "Swagger: http://127.0.0.1:8104/docs"
"$ROOT_DIR/deploy/local/start-api.sh" & API_PID=$!
"$ROOT_DIR/deploy/local/start-web.sh" & WEB_PID=$!
cleanup(){ kill "$API_PID" "$WEB_PID" 2>/dev/null || true; wait "$API_PID" "$WEB_PID" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
wait -n "$API_PID" "$WEB_PID"
