from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values

API_DIR = Path(__file__).resolve().parents[1]
CONFIG_FILES = ("app.env", "auth.env", "database.env", "services.env")
CONFIG_CONTEXT = "local" if "/home/daniel/" in API_DIR.as_posix() else "production"
CONFIG_DIR = API_DIR / "config" / CONFIG_CONTEXT


def get_config_context() -> str:
    return CONFIG_CONTEXT


def get_config_files(context: str | None = None) -> tuple[Path, ...]:
    selected = context or CONFIG_CONTEXT
    if selected not in {"local", "production"}:
        raise RuntimeError("Contexto de configuração deve ser local ou production.")
    directory = API_DIR / "config" / selected
    files = tuple(directory / name for name in CONFIG_FILES)
    missing = [str(path) for path in files if not path.is_file()]
    if missing:
        raise RuntimeError("Arquivos de configuração ausentes: " + ", ".join(missing))
    return files


def load_config_values(context: str | None = None) -> dict[str, str]:
    values: dict[str, str] = {}
    origins: dict[str, Path] = {}
    for path in get_config_files(context):
        for key, raw_value in dotenv_values(path).items():
            if raw_value is None:
                continue
            if key in values:
                raise RuntimeError(f"Variável duplicada {key} em {origins[key]} e {path}.")
            values[key] = str(raw_value)
            origins[key] = path
    return values


def load_config_environment(context: str | None = None, *, overwrite: bool = True) -> dict[str, str]:
    values = load_config_values(context)
    for key, value in values.items():
        if overwrite or key not in os.environ:
            os.environ[key] = value
    return values
