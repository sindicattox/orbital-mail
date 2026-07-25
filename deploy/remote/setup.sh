#!/usr/bin/env bash
# cd /home/ubuntu/apps/orbital-mail
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"
./deploy/local/setup-api.sh
./deploy/local/setup-web.sh
cd apps/web
npm run build
echo "Build remoto preparado."
