#!/usr/bin/env bash
set -euo pipefail
D="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PIDS=()
cleanup() {
  ((${#PIDS[@]})) && kill "${PIDS[@]}" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM
echo "Preparando e iniciando API e Web locais."
"$D/setup-api.sh" & PIDS+=("$!")
"$D/setup-web.sh" & PIDS+=("$!")
wait -n "${PIDS[@]}"
