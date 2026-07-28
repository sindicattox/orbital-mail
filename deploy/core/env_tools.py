#!/usr/bin/env python3
import sys
from pathlib import Path


def set_values(source: Path, target: Path, assignments: list[str]) -> None:
    values: dict[str, str] = {}
    for assignment in assignments:
        if "=" not in assignment:
            raise SystemExit(f"Variável inválida: {assignment}")
        key, value = assignment.split("=", 1)
        values[key] = value

    lines = source.read_text(encoding="utf-8").splitlines()
    written: set[str] = set()
    output: list[str] = []

    for line in lines:
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            output.append(line)
            continue
        key = line.split("=", 1)[0].strip()
        if key in values:
            output.append(f"{key}={values[key]}")
            written.add(key)
        else:
            output.append(line)

    for key, value in values.items():
        if key not in written:
            output.append(f"{key}={value}")

    target.write_text("\n".join(output) + "\n", encoding="utf-8")


def main() -> None:
    if len(sys.argv) < 4 or sys.argv[1] != "set":
        raise SystemExit("Uso: env_tools.py set ORIGEM DESTINO CHAVE=VALOR [...]")
    source = Path(sys.argv[2])
    target = Path(sys.argv[3])
    if not source.is_file():
        raise SystemExit(f"Arquivo obrigatório não encontrado: {source}")
    set_values(source, target, sys.argv[4:])


if __name__ == "__main__":
    main()
