#!/usr/bin/env python
"""Schema Guard

Checks:
 1. Canonical file exists: backend/graphql/schema.graphql
 2. Mirror file exists:    graphql/schema.graphql
 3. No unexpected duplicates matching **/backend/backend/graphql/schema.graphql
 4. Canonical and mirror contents (after stripping leading/trailing
     whitespace) are identical.

Exit codes:
 0 OK
 1 Missing canonical
 2 Missing mirror
 3 Duplicate legacy file present
 4 Contents differ

Usage:
  python scripts/schema_guard.py

Integrate in CI or local preflight before release.
"""
from __future__ import annotations
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
CANON = ROOT / "backend" / "graphql" / "schema.graphql"
MIRROR = ROOT / "graphql" / "schema.graphql"
LEGACY = ROOT / "backend" / "backend" / "graphql" / "schema.graphql"

def main() -> int:
    if not CANON.exists():
        print(
            f"[SCHEMA GUARD] Missing canonical schema: {CANON}",
            file=sys.stderr,
        )
        return 1
    if not MIRROR.exists():
        print(
            f"[SCHEMA GUARD] Missing mirror schema: {MIRROR}",
            file=sys.stderr,
        )
        return 2
    if LEGACY.exists():
        print(
            f"[SCHEMA GUARD] Legacy duplicate present (remove it): {LEGACY}",
            file=sys.stderr,
        )
        return 3
    canon_txt = CANON.read_text(encoding="utf-8").strip()
    mirror_txt = MIRROR.read_text(encoding="utf-8").strip()
    if canon_txt != mirror_txt:
        print(
            "[SCHEMA GUARD] Canonical and mirror schema differ.",
            file=sys.stderr,
        )
        return 4
    print("[SCHEMA GUARD] OK (canonical + mirror in sync)")
    return 0



if __name__ == "__main__":
    raise SystemExit(main())
