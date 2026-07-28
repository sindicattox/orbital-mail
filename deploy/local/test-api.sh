#!/usr/bin/env bash
set -euo pipefail
R="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON="$R/apps/api/.venv/bin/python"
[[ -x "$PYTHON" ]] || PYTHON=python3
cd "$R"
"$PYTHON" -m pytest -q
