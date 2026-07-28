#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PYTHON="$ROOT_DIR/apps/api/.venv/bin/python"
[[ -x "$PYTHON" ]] || PYTHON=python3
cd "$ROOT_DIR"
"$PYTHON" -m pytest -q
node --check apps/web/public/components/mail.js
node --check apps/web/public/components/mail/shared.js
node --check apps/web/public/components/mail/styles.js
node --check apps/web/src/components/orbital-html-editor/editor.js
node --check apps/web/src/assets/auth/orbital-mail-auth.js
cd apps/web
npm run check
npm run build
echo "Testes locais concluídos."
