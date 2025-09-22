#!/usr/bin/env python3
"""Stub di compatibilità: reindirizza allo script unificato in root.

Motivazione: mantenere i workflow GitHub che puntano a questo percorso
evitando duplicazione della logica di diff semantico.
"""
from __future__ import annotations
import runpy
import sys
from pathlib import Path

ROOT_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "verify_schema_breaking.py"

if not ROOT_SCRIPT.exists():  # pragma: no cover
    sys.stderr.write("Script unificato mancante: scripts/verify_schema_breaking.py\n")
    sys.exit(2)

if __name__ == "__main__":  # pragma: no cover
    runpy.run_path(str(ROOT_SCRIPT), run_name="__main__")
