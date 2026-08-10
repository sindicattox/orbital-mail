#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${1:?Informe o diretório remoto da aplicação.}"
shift
(( $# > 0 )) || { echo "Informe ao menos um serviço systemd." >&2; exit 1; }

[[ "$ROOT_DIR" == /* && "$ROOT_DIR" != *'..'* && "$ROOT_DIR" =~ ^/[A-Za-z0-9._/-]+$ ]] || {
    echo "Diretório remoto inválido: $ROOT_DIR" >&2
    exit 1
}

SYSTEMD_DIR="$ROOT_DIR/deploy/remote/systemd"
REMOTE_USER="$(id -un)"
REMOTE_GROUP="$(id -gn)"
CHANGED=false
SERVICES=("$@")

for service in "${SERVICES[@]}"; do
    [[ "$service" =~ ^[A-Za-z0-9_.@:-]+\.service$ ]] || { echo "Serviço systemd inválido: $service" >&2; exit 1; }
    source_file="$SYSTEMD_DIR/$service"
    target_file="/etc/systemd/system/$service"
    [[ -s "$source_file" ]] || { echo "Unit do módulo não encontrada: $source_file" >&2; exit 1; }

    rendered="$(mktemp)"
    sed -e "s|__REMOTE_ROOT__|$ROOT_DIR|g" -e "s|__REMOTE_USER__|$REMOTE_USER|g" -e "s|__REMOTE_GROUP__|$REMOTE_GROUP|g" "$source_file" > "$rendered"
    if ! cmp -s "$rendered" "$target_file"; then
        sudo install -m 0644 "$rendered" "$target_file"
        CHANGED=true
    fi
    rm -f "$rendered"
done

if [[ "$CHANGED" == true ]]; then
    sudo systemctl daemon-reload
fi

for service in "${SERVICES[@]}"; do
    sudo systemctl enable "$service" >/dev/null
done
