#!/usr/bin/env bash
set -euo pipefail
D="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$D/test-api.sh"
"$D/test-web.sh"
echo "Testes locais concluídos."
