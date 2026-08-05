#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"
[[ -x apps/api/.venv/bin/pytest ]] || { echo "Execute ./deploy/local/setup-api.sh primeiro." >&2; exit 1; }
apps/api/.venv/bin/pytest -q tests
