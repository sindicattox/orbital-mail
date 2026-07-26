#!/usr/bin/env bash
# cd /home/ubuntu/apps/orbital-mail
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
[[ -f "$ROOT_DIR/apps/api/.env" ]] || { echo "Arquivo da API ausente: $ROOT_DIR/apps/api/.env" >&2; exit 1; }
[[ -f "$ROOT_DIR/apps/web/.env" ]] || { echo "Arquivo da Web ausente: $ROOT_DIR/apps/web/.env" >&2; exit 1; }
cd "$ROOT_DIR"
./deploy/local/setup-api.sh

cd "$ROOT_DIR/apps/api"
.venv/bin/python - <<'PY'
from core.settings import get_settings

settings = get_settings()
if settings.app_env.strip().lower() not in {"production", "prod", "remote"}:
    raise SystemExit("APP_ENV deve ser production no servidor.")
print(f"Configuração validada: {settings.app_service} / {settings.app_env}")
PY

cd "$ROOT_DIR"
./deploy/local/setup-web.sh
cd apps/web
npm run check
npm run build
echo "Build remoto preparado."
