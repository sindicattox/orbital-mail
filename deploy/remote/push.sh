#!/usr/bin/env bash
# cd /home/daniel/Code/orgs/orbital/orbital-mail
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="$ROOT_DIR/deploy/remote/.env"
[[ -f "$ENV_FILE" ]] || { echo "Crie $ENV_FILE a partir de .env.example" >&2; exit 1; }
set -a; source "$ENV_FILE"; set +a
REMOTE_HOST="${DEPLOY_REMOTE_HOST:?DEPLOY_REMOTE_HOST obrigatório}"
REMOTE_DIR="${DEPLOY_REMOTE_DIR:?DEPLOY_REMOTE_DIR obrigatório}"
echo "[orbital-mail] enviando para $REMOTE_HOST:$REMOTE_DIR"
ssh "$REMOTE_HOST" "mkdir -p '$REMOTE_DIR'"
rsync -az --delete \
  --exclude '.git/' --exclude '.env' --exclude '.venv/' --exclude 'node_modules/' --exclude 'dist/' --exclude '.astro/' \
  "$ROOT_DIR/" "$REMOTE_HOST:$REMOTE_DIR/"
