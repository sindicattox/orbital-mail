#!/usr/bin/env bash
set -euo pipefail
D="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$D/start-api.sh"
"$D/start-web.sh"
echo "Aplicação remota iniciada e validada."
