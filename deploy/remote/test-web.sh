#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; source "${DEPLOY_TARGET_FILE:-$SCRIPT_DIR/target.conf}"
ssh -i "$DEPLOY_SSH_KEY" -o BatchMode=yes "$DEPLOY_REMOTE_HOST" 'bash -s' -- "$DEPLOY_REMOTE_ROOT" <<'REMOTE'
set -euo pipefail
ROOT_DIR="$1"; source "$ROOT_DIR/deploy/core/load-env.sh"; load_config_context "$ROOT_DIR/apps/web"; cd "$ROOT_DIR/apps/web"; npm run check; npm run build
REMOTE
