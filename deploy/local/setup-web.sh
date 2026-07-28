#!/usr/bin/env bash
set -euo pipefail
D="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
R="$(cd "$D/../.." && pwd)"
WEB="$R/apps/web"
ENV="$WEB/.env"
UI="$(dirname "$R")/orbital-ui"
[[ -f "$ENV" ]] || cp "$WEB/.env.example" "$ENV"
PORT="$(sed -n -e 's/^APP_PORT=//p' -e 's/^PORT=//p' "$ENV" | tail -n 1 | tr -d '\r"'\'' ')"
[[ "$PORT" =~ ^[0-9]+$ ]] || { echo "APP_PORT/PORT inválida em $ENV" >&2; exit 1; }
[[ -f "$UI/package.json" ]] || { echo "Dependência ausente: $UI/package.json" >&2; exit 1; }
command -v fuser >/dev/null || { echo "fuser não encontrado." >&2; exit 1; }
echo "Parando Web local e liberando a porta $PORT."
fuser -k "$PORT/tcp" >/dev/null 2>&1 || true
echo "Preparando Web em $WEB."
cd "$WEB"
rm -rf .astro dist
npm ci
echo "Web preparada."
exec "$D/start-web.sh"
