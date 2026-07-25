#!/usr/bin/env bash
# cd /home/ubuntu/apps/orbital-mail
set -euo pipefail
sudo systemctl restart orbital-mail-api.service
sudo systemctl restart orbital-mail-web.service
sudo systemctl --no-pager --full status orbital-mail-api.service orbital-mail-web.service
