#!/usr/bin/env bash
set -euo pipefail

load_env_file() {
    local file="$1" line key value
    [[ -f "$file" ]] || return 0
    while IFS= read -r line || [[ -n "$line" ]]; do
        [[ -z "$line" ]] && continue
        [[ "$line" == *=* ]] || {
            echo "Linha inválida em $file: $line" >&2
            return 1
        }
        key="${line%%=*}"
        value="${line#*=}"
        [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || {
            echo "Variável inválida em $file: $key" >&2
            return 1
        }
        if [[ ${#value} -ge 2 ]]; then
            if [[ "${value:0:1}" == '"' && "${value: -1}" == '"' ]]; then
                value="${value:1:${#value}-2}"
            elif [[ "${value:0:1}" == "'" && "${value: -1}" == "'" ]]; then
                value="${value:1:${#value}-2}"
            fi
        fi
        printf -v "$key" '%s' "$value"
        export "$key"
    done < "$file"
}

load_config_context() {
    local app_dir="$1" context="production" config_root="$1/config" file
    [[ "$app_dir" == /home/daniel/* ]] && context="local"
    [[ -d "$config_root/$context" ]] || {
        echo "Diretório de configuração ausente: $config_root/$context" >&2
        return 1
    }
    for file in app.env auth.env database.env services.env; do
        load_env_file "$config_root/$context/$file"
    done
}
