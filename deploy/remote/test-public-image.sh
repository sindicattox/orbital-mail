#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
PYTHON="$API_DIR/.venv/bin/python"
TENANT_CODE="${1:-}"

if [[ -z "$TENANT_CODE" ]]; then
    echo "Uso: ./deploy/remote/test-public-image.sh <tenant_code>" >&2
    echo "Exemplo: ./deploy/remote/test-public-image.sh anpprev" >&2
    exit 2
fi
if [[ ! "$TENANT_CODE" =~ ^[A-Za-z0-9_-]+$ ]]; then
    echo "Tenant inválido: $TENANT_CODE" >&2
    exit 2
fi
[[ -x "$PYTHON" ]] || { echo "Ambiente Python ausente: $PYTHON" >&2; exit 1; }
[[ -f "$API_DIR/.env" ]] || { echo "Configuração ausente: $API_DIR/.env" >&2; exit 1; }

mapfile -t PROBE < <(
    cd "$API_DIR"
    "$PYTHON" - "$TENANT_CODE" <<'PY'
import base64
import sys
from uuid import uuid4

from core.settings import get_settings
from mail.image_storage import tenant_upload_dir

tenant = sys.argv[1].strip().lower()
settings = get_settings()
directory = tenant_upload_dir(settings, tenant)
directory.mkdir(parents=True, exist_ok=True)
filename = f"{uuid4().hex}.png"
path = directory / filename
# PNG 1x1 transparente, usado apenas durante o smoke test.
payload = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)
path.write_bytes(payload)
print(path)
print(f"{settings.mail_public_upload_url.rstrip('/')}/{tenant}/{filename}")
PY
)

FILE_PATH="${PROBE[0]:-}"
PUBLIC_URL="${PROBE[1]:-}"
[[ -n "$FILE_PATH" && -n "$PUBLIC_URL" ]] || { echo "Falha ao preparar imagem temporária." >&2; exit 1; }

RESPONSE_FILE="$(mktemp)"
HEADERS_FILE="$(mktemp)"
cleanup() {
    rm -f "$FILE_PATH" "$RESPONSE_FILE" "$HEADERS_FILE"
}
trap cleanup EXIT

echo "[public-image] tenant: $TENANT_CODE"
echo "[public-image] arquivo: $FILE_PATH"
echo "[public-image] URL: $PUBLIC_URL"

HTTP_CODE="$(curl -sS --max-time 20 -D "$HEADERS_FILE" -o "$RESPONSE_FILE" -w '%{http_code}' "$PUBLIC_URL")"
if [[ "$HTTP_CODE" != "200" ]]; then
    echo "[public-image] ERRO: esperado HTTP 200, recebido HTTP $HTTP_CODE" >&2
    sed -n '1,40p' "$HEADERS_FILE" >&2
    exit 1
fi
if ! grep -Eiq '^content-type:[[:space:]]*image/png([;[:space:]]|$)' "$HEADERS_FILE"; then
    echo "[public-image] ERRO: Content-Type não é image/png" >&2
    sed -n '1,40p' "$HEADERS_FILE" >&2
    exit 1
fi
if ! cmp -s "$FILE_PATH" "$RESPONSE_FILE"; then
    echo "[public-image] ERRO: conteúdo publicado difere do arquivo físico." >&2
    exit 1
fi

echo "[public-image] OK: Nginx/HTTPS -> API -> storage do tenant retornou a imagem correta."
