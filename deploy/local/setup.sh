#!/usr/bin/env bash
# cd /home/daniel/Code/orgs/orbital/orbital-mail
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
"$ROOT_DIR/deploy/local/setup-api.sh"
"$ROOT_DIR/deploy/local/setup-web.sh"
echo "Ambiente local pronto. Execute ./deploy/local/start.sh."
