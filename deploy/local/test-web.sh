#!/usr/bin/env bash
set -euo pipefail
R="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
node --check "$R/apps/web/public/components/mail.js"
node --check "$R/apps/web/public/components/mail/shared.js"
node --check "$R/apps/web/public/components/mail/styles.js"
node --check "$R/apps/web/src/components/orbital-html-editor/editor.js"
node --check "$R/apps/web/src/assets/auth/orbital-mail-auth.js"
cd "$R/apps/web"
npm run check
npm run build
