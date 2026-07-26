#!/usr/bin/env bash
set -euo pipefail

wait_url() {
    local url="$1"
    local attempts="${2:-15}"
    local delay="${3:-2}"

    for ((attempt = 1; attempt <= attempts; attempt++)); do
        curl -fsS --max-time 10 "$url" >/dev/null && return 0
        sleep "$delay"
    done

    echo "Endpoint indisponível após $attempts tentativas: $url" >&2
    return 1
}

trap 'sudo systemctl --no-pager --full --lines=60 status orbital-mail-api.service orbital-mail-web.service || true' ERR

sudo systemctl restart orbital-mail-api.service orbital-mail-web.service

wait_url http://127.0.0.1:8104/api/health
wait_url http://127.0.0.1:8104/api/health/db 20 2
wait_url http://127.0.0.1:4104/

sudo systemctl --no-pager --full status orbital-mail-api.service orbital-mail-web.service
echo "[orbital-mail] API, banco e Web disponíveis."
