#!/usr/bin/env bash
# cd /home/ubuntu/apps/orbital-mail
set -euo pipefail
sudo journalctl -u orbital-mail-api.service -u orbital-mail-web.service -f
