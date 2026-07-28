#!/usr/bin/env bash
set -euo pipefail
D="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$D/target.conf"
SSH=(-i "$DEPLOY_SSH_KEY" -o BatchMode=yes -o ConnectTimeout=15)
ssh "${SSH[@]}" "$DEPLOY_REMOTE_HOST" 'bash -s' -- "$DEPLOY_REMOTE_ROOT" <<'REMOTE'
set -euo pipefail
ROOT="$1"
node --check "$ROOT/apps/web/public/components/mail.js"
node --check "$ROOT/apps/web/public/components/mail/shared.js"
node --check "$ROOT/apps/web/public/components/mail/styles.js"
node --check "$ROOT/apps/web/src/components/orbital-html-editor/editor.js"
node --check "$ROOT/apps/web/src/assets/auth/orbital-mail-auth.js"
cd "$ROOT/apps/web"
npm run check
npm run build
REMOTE
