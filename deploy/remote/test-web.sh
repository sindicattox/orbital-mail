#!/usr/bin/env bash
# Executa check e build da Web do Orbital Mail no servidor definido em target.conf.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_FILE="${DEPLOY_TARGET_FILE:-$SCRIPT_DIR/target.conf}"
[[ -f "$TARGET_FILE" ]] || { echo "Destino obrigatório não encontrado: $TARGET_FILE" >&2; exit 1; }
set -a
# shellcheck source=/dev/null
source "$TARGET_FILE"
set +a
SSH_KEY="${DEPLOY_SSH_KEY:-$HOME/amazon.ssh}"
REMOTE_HOST="${DEPLOY_REMOTE_HOST:?Defina DEPLOY_REMOTE_HOST em $TARGET_FILE}"
REMOTE_ROOT="${DEPLOY_REMOTE_ROOT:?Defina DEPLOY_REMOTE_ROOT em $TARGET_FILE}"
SSH_OPTIONS=(-i "$SSH_KEY" -o BatchMode=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=120 -o TCPKeepAlive=yes)

ssh "${SSH_OPTIONS[@]}" "$REMOTE_HOST" 'bash -s' -- "$REMOTE_ROOT" <<'REMOTE'
set -euo pipefail
ROOT_DIR="$1"
cd "$ROOT_DIR/apps/web"
[[ -d node_modules ]] || { echo "Execute ./deploy/remote/setup-web.sh primeiro." >&2; exit 1; }
npm run check
npm run build
REMOTE
