#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_FILE="${DEPLOY_TARGET_FILE:-$SCRIPT_DIR/target.conf}"

[[ -f "$TARGET_FILE" ]] || { echo "Destino não encontrado: $TARGET_FILE" >&2; exit 1; }
# shellcheck source=/dev/null
source "$TARGET_FILE"

SSH_KEY="${DEPLOY_SSH_KEY:?Defina DEPLOY_SSH_KEY em $TARGET_FILE}"
REMOTE_HOST="${DEPLOY_REMOTE_HOST:?Defina DEPLOY_REMOTE_HOST em $TARGET_FILE}"
LOCAL_DIR="${DEPLOY_LOCAL_WALLET_DIR:?Defina DEPLOY_LOCAL_WALLET_DIR em $TARGET_FILE}"
REMOTE_DIR="${DEPLOY_REMOTE_WALLET_DIR:?Defina DEPLOY_REMOTE_WALLET_DIR em $TARGET_FILE}"
SSH=(-i "$SSH_KEY" -o BatchMode=yes -o ConnectTimeout=15 -o ServerAliveInterval=30 -o ServerAliveCountMax=120)

[[ -d "$LOCAL_DIR" ]] || { echo "Wallet local não encontrada: $LOCAL_DIR" >&2; exit 1; }
for file in tnsnames.ora sqlnet.ora cwallet.sso; do
    [[ -f "$LOCAL_DIR/$file" ]] || { echo "Arquivo obrigatório ausente: $LOCAL_DIR/$file" >&2; exit 1; }
done

command -v rsync >/dev/null || { echo "rsync não encontrado localmente." >&2; exit 1; }
echo "Enviando Wallet para $REMOTE_HOST:$REMOTE_DIR..."
ssh "${SSH[@]}" "$REMOTE_HOST" "mkdir -p $(printf '%q' "$REMOTE_DIR")"
rsync -az --delete -e "ssh ${SSH[*]}" "$LOCAL_DIR/" "$REMOTE_HOST:$REMOTE_DIR/"
ssh "${SSH[@]}" "$REMOTE_HOST" "chmod 700 $(printf '%q' "$REMOTE_DIR"); find $(printf '%q' "$REMOTE_DIR") -type f -exec chmod 600 {} +"
echo "Wallet enviada. Reiniciando API e workers..."
"$SCRIPT_DIR/start-api.sh"
