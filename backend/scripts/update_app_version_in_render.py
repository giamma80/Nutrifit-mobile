"""Utility per aggiornare APP_VERSION nel file render.yaml di root.

Uso:
  python backend/scripts/update_app_version_in_render.py <nuova_versione>

Comportamento:
  - Legge il file 'render.yaml' nella root repo
  - Sostituisce il valore della chiave APP_VERSION nella prima occorrenza
  - Verifica che la versione rispetti un pattern semver semplice
  - Stampa la versione aggiornata su stdout

Da integrare nella pipeline di release prima del commit/tag.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:[-+][A-Za-z0-9_.-]+)?$")


def update_version(file_path: Path, new_version: str) -> None:
    text = file_path.read_text(encoding="utf-8").splitlines()
    updated = False
    for idx, line in enumerate(text):
        # linea del tipo: - key: APP_VERSION  /   value: 0.0.0-dev
        if "- key: APP_VERSION" in line:
            # la value dovrebbe essere nella riga successiva (indentata)
            next_line_is_value = idx + 1 < len(text) and text[idx + 1].strip().startswith("value:")
            if next_line_is_value:
                old = text[idx + 1]
                # sostituisce tutto dopo 'value:' mantenendo indentazione
                prefix = old.split("value:", 1)[0] + "value: "
                text[idx + 1] = f"{prefix}{new_version}"
                updated = True
                break
    if not updated:
        raise SystemExit("APP_VERSION non trovata in render.yaml")
    file_path.write_text("\n".join(text) + "\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Uso: python backend/scripts/update_app_version_in_render.py " "<nuova_versione>")
        return 1
    new_version = argv[1].strip()
    if not SEMVER_RE.match(new_version):
        print(
            "Versione '" + new_version + "' non valida (atteso semver "
            "x.y.z[+metadata|-prerelease])"
        )
        return 2
    file_path = Path(__file__).resolve().parent.parent.parent / "render.yaml"
    if not file_path.exists():
        print("render.yaml non trovato nella root del repository")
        return 3
    update_version(file_path, new_version)
    print(new_version)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv))
