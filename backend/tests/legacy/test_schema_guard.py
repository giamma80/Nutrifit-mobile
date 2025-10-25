from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = ROOT / "scripts" / "schema_guard.py"


def test_schema_guard_ok() -> None:
    assert SCRIPT.exists(), "schema_guard.py missing"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        # Include stdout/stderr nel messaggio per diagnosi rapida
        msg = (
            "schema_guard failed: code="
            f"{proc.returncode}\nSTDOUT\n---\n"
            f"{proc.stdout}\nSTDERR\n---\n{proc.stderr}"
        )
        raise AssertionError(msg)
