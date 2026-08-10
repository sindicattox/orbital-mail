#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
PYTHON="$API_DIR/.venv/bin/python"
UVICORN="$API_DIR/.venv/bin/uvicorn"

[[ -x "$PYTHON" && -x "$UVICORN" ]] || {
    echo "API não preparada. Execute setup-api.sh." >&2
    exit 1
}

cd "$API_DIR"
"$PYTHON" -c 'from core.settings import get_settings; get_settings()'
read -r API_HOST API_PORT < <("$PYTHON" -c 'from core.settings import get_settings; s=get_settings(); print(s.app_host, s.app_port)')

PIDS=()

cleanup() {
    trap - INT TERM EXIT

    local pid
    for pid in "${PIDS[@]}"; do
        kill -TERM -- "-$pid" 2>/dev/null || true
    done

    sleep 0.2

    for pid in "${PIDS[@]}"; do
        kill -KILL -- "-$pid" 2>/dev/null || true
    done

    wait 2>/dev/null || true
}

trap cleanup INT TERM EXIT

echo "Iniciando API local em ${API_HOST}:${API_PORT}..."
setsid "$UVICORN" main:app --reload --host "$API_HOST" --port "$API_PORT" &
API_PID="$!"
PIDS+=("$API_PID")

for _ in {1..30}; do
    kill -0 "$API_PID" 2>/dev/null || {
        echo "Erro: API local encerrou durante a inicialização." >&2
        exit 1
    }
    if curl -fsS --max-time 2 "http://127.0.0.1:${API_PORT}/api/health" >/dev/null 2>&1; then
        echo "API local iniciada."
        wait -n "${PIDS[@]}"
        exit $?
    fi

    sleep 1
done

echo "Erro: API local não ficou pronta." >&2
exit 1
