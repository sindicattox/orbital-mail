#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "$ROOT_DIR/deploy/core/load-env.sh"
load_config_context "$ROOT_DIR/apps/web"
cd "$ROOT_DIR/apps/web"
npm run check
npm run build
