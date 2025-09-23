from __future__ import annotations
import subprocess
import sys
from pathlib import Path


def run_guard() -> subprocess.CompletedProcess[str]:
    ROOT = Path(__file__).resolve().parent.parent.parent
    script = ROOT / "scripts" / "schema_guard.py"
    return subprocess.run([sys.executable, str(script)], capture_output=True, text=True)


def test_schema_guard_detects_divergence(tmp_path: Path) -> None:
    ROOT = Path(__file__).resolve().parent.parent.parent
    # Percorsi file
    mirror = ROOT / "graphql" / "schema.graphql"
    original = mirror.read_text(encoding="utf-8")
    try:
        # Introduce una divergenza minima (spazio extra)
        mirror.write_text(original + "\n# divergence", encoding="utf-8")
        proc = run_guard()
        assert proc.returncode == 4, (
            "Expected exit 4 for divergence, got " f"{proc.returncode}. stderr={proc.stderr}"
        )
    finally:
        mirror.write_text(original, encoding="utf-8")
        # Sanity: guard torna verde
        proc2 = run_guard()
        assert proc2.returncode == 0, (
            "Guard should be green after restore, got " f"{proc2.returncode}"
        )
