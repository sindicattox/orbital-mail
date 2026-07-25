#!/usr/bin/env bash
# cd /home/ubuntu/apps/orbital-mail
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
sudo cp "$ROOT_DIR/deploy/remote/systemd/orbital-mail-api.service" /etc/systemd/system/
sudo cp "$ROOT_DIR/deploy/remote/systemd/orbital-mail-web.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable orbital-mail-api.service orbital-mail-web.service
echo "Serviços instalados e habilitados."
