#!/usr/bin/env bash
set -euo pipefail
D="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIDS=()
cleanup() {
  ((${#PIDS[@]})) && kill "${PIDS[@]}" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM
echo "Iniciando API e Web locais."
"$D/start-api.sh" & PIDS+=("$!")
"$D/start-web.sh" & PIDS+=("$!")
wait -n "${PIDS[@]}"
