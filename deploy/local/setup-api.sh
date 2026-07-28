#!/usr/bin/env bash
set -euo pipefail
D="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
R="$(cd "$D/../.." && pwd)"
API="$R/apps/api"
ENV="$API/.env"
[[ -f "$ENV" ]] || cp "$API/.env.example" "$ENV"
PORT="$(sed -n 's/^APP_PORT=//p' "$ENV" | tail -n 1 | tr -d '\r"'\'' ')"
[[ "$PORT" =~ ^[0-9]+$ ]] || { echo "APP_PORT inválida em $ENV" >&2; exit 1; }
command -v fuser >/dev/null || { echo "fuser não encontrado." >&2; exit 1; }
echo "Parando API local e liberando a porta $PORT."
fuser -k "$PORT/tcp" >/dev/null 2>&1 || true
echo "Preparando API em $API."
rm -rf "$API/.venv"
python3 -m venv "$API/.venv"
"$API/.venv/bin/python" -m pip install --upgrade pip
"$API/.venv/bin/pip" install -r "$API/requirements.txt"
echo "API preparada."
exec "$D/start-api.sh"
