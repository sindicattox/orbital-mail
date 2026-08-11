#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
APP_CONFIG="$API_DIR/config/local/app.env"
PYTHON="$API_DIR/.venv/bin/python"

[[ -f "$APP_CONFIG" ]] || { echo "Configuração da API não encontrada: $APP_CONFIG" >&2; exit 1; }
API_PORT="$(sed -n 's/^APP_PORT=//p' "$APP_CONFIG")"
[[ "$API_PORT" =~ ^[0-9]+$ ]] && ((API_PORT >= 1 && API_PORT <= 65535)) || { echo "APP_PORT inválido." >&2; exit 1; }

is_project_worker() {
    local pid="$1"
    local proc_dir="/proc/$pid"
    local cwd cmdline

    [[ -r "$proc_dir/cmdline" ]] || return 1
    cwd="$(readlink -f "$proc_dir/cwd" 2>/dev/null || true)"
    [[ "$cwd" == "$API_DIR" ]] || return 1
    cmdline="$(tr '\0' ' ' < "$proc_dir/cmdline" 2>/dev/null || true)"
    [[ " $cmdline " == *" -m workers.mail_send_worker "* ]]
}

stop_worker() {
    local proc_dir pid
    local -a pids=()

    for proc_dir in /proc/[0-9]*; do
        pid="${proc_dir##*/}"
        is_project_worker "$pid" && pids+=("$pid")
    done

    ((${#pids[@]})) || return 0

    for pid in "${pids[@]}"; do
        echo "Parando mail worker local existente (PID $pid)..."
        kill -TERM "$pid" 2>/dev/null || true
    done

    for _ in {1..30}; do
        local alive=0
        for pid in "${pids[@]}"; do
            is_project_worker "$pid" && alive=1 && break
        done
        ((alive == 0)) && return 0
        sleep 0.1
    done

    for pid in "${pids[@]}"; do
        if is_project_worker "$pid"; then
            echo "Forçando parada do mail worker local (PID $pid)..." >&2
            kill -KILL "$pid" 2>/dev/null || true
        fi
    done
}

api_pids() {
    fuser "${API_PORT}/tcp" 2>/dev/null | xargs || true
}

OLD_API_PIDS="$(api_pids)"
stop_worker

API_READY=false
for _ in {1..300}; do
    CURRENT_API_PIDS="$(api_pids)"
    if [[ -n "$CURRENT_API_PIDS" && "$CURRENT_API_PIDS" != "$OLD_API_PIDS" ]] \
        && curl -fsS --max-time 2 "http://127.0.0.1:${API_PORT}/api/health/worker" >/dev/null 2>&1; then
        API_READY=true
        break
    fi
    sleep 1
done

[[ "$API_READY" == true ]] || {
    echo "Erro: API local não ficou pronta para iniciar o mail worker." >&2
    exit 1
}
[[ -x "$PYTHON" ]] || { echo "API não preparada. Execute setup.sh." >&2; exit 1; }

cd "$API_DIR"
echo "Iniciando mail worker local..."
setsid "$PYTHON" -m workers.mail_send_worker &
WORKER_PID="$!"

cleanup() {
    trap - INT TERM EXIT
    kill -TERM -- "-$WORKER_PID" 2>/dev/null || true
    sleep 0.2
    kill -KILL -- "-$WORKER_PID" 2>/dev/null || true
    wait "$WORKER_PID" 2>/dev/null || true
}
trap cleanup INT TERM EXIT

for _ in {1..30}; do
    kill -0 "$WORKER_PID" 2>/dev/null || {
        echo "Erro: mail worker local encerrou durante a inicialização." >&2
        exit 1
    }
    if curl -fsS --max-time 2 "http://127.0.0.1:${API_PORT}/api/health/worker" >/dev/null 2>&1; then
        echo "Mail worker local iniciado."
        wait "$WORKER_PID"
        exit $?
    fi
    sleep 1
done

echo "Erro: mail worker local não ficou pronto." >&2
exit 1
