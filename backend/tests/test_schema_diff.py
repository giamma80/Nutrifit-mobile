import json
from pathlib import Path
import subprocess
import textwrap
import sys
from typing import Tuple
from contextlib import suppress


# Root repo: /<repo>/backend/tests -> parents[2]
REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "backend" / "scripts" / "verify_schema_breaking.py"


def run_diff(mirror_sdl: str, backend_sdl: str) -> Tuple[int, str]:
    """Esegue il diff senza lasciare side-effect permanenti sui file schema.

    Salva il contenuto precedente (se esiste), scrive i due SDL forniti,
    invoca lo script e poi ripristina gli originali in un blocco finally.
    """
    mirror = REPO_ROOT / "graphql" / "schema.graphql"
    backend = REPO_ROOT / "backend" / "graphql" / "schema.graphql"
    mirror.parent.mkdir(parents=True, exist_ok=True)
    backend.parent.mkdir(parents=True, exist_ok=True)
    prev_mirror = mirror.read_text(encoding="utf-8") if mirror.exists() else None
    prev_backend = backend.read_text(encoding="utf-8") if backend.exists() else None
    try:
        mirror.write_text(mirror_sdl, encoding="utf-8")
        backend.write_text(backend_sdl, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(SCRIPT)],
            capture_output=True,
            text=True,
        )
        return proc.returncode, proc.stdout
    finally:
        if prev_mirror is not None:
            with suppress(Exception):
                mirror.write_text(prev_mirror, encoding="utf-8")
        if prev_backend is not None:
            with suppress(Exception):
                backend.write_text(prev_backend, encoding="utf-8")


def _wrap(s: str) -> str:
    return textwrap.dedent(s).strip() + "\n"


def test_additive_field() -> None:
    mirror = _wrap(
        """
    type A { id: ID! }
    type Query { a: A }
    """
    )
    backend = _wrap(
        """
    type A { id: ID! name: String }
    type Query { a: A }
    """
    )
    code, out = run_diff(mirror, backend)
    data = json.loads(out)
    assert code == 0
    assert data["classification"] == "additive"
    assert "name" in data["added_fields"]["A"]


def test_breaking_field_removed() -> None:
    mirror = _wrap(
        """
    type A { id: ID! name: String }
    type Query { a: A }
    """
    )
    backend = _wrap(
        """
    type A { id: ID! }
    type Query { a: A }
    """
    )
    code, out = run_diff(mirror, backend)
    data = json.loads(out)
    assert code == 1
    assert data["classification"] in ("breaking", "mixed")
    assert "name" in data["removed_fields"]["A"]


def test_enum_deprecation_and_add_value() -> None:
    mirror = _wrap(
        """
    enum E { A }
    type Query { _q: String }
    """
    )
    backend = _wrap(
        """
    enum E { A B @deprecated(reason: "legacy") }
    type Query { _q: String }
    """
    )
    code, out = run_diff(mirror, backend)
    data = json.loads(out)
    assert code == 0
    assert data["classification"] == "additive"
    assert "B" in data["added_enum_values"]["E"]


def test_interface_mismatch() -> None:
    mirror = _wrap(
        """
    interface Node { id: ID! }
    type A implements Node { id: ID! name: String }
    type Query { a: A }
    """
    )
    backend = _wrap(
        """
    interface Node { id: ID! }
    type A implements Node { name: String }
    type Query { a: A }
    """
    )
    code, out = run_diff(mirror, backend)
    data = json.loads(out)
    assert code == 1
    assert data["classification"] in ("breaking", "mixed")
    assert any("mancante" in x for x in data["interface_breaks"]["A"])


def test_multiple_interface_implements_breaking() -> None:
    mirror = _wrap(
        """
    interface Node { id: ID! }
    interface Named { name: String }
    type A implements Node & Named { id: ID! name: String }
    type Query { a: A }
    """
    )
    backend = _wrap(
        """
    interface Node { id: ID! }
    interface Named { name: String }
    type A implements Node & Named { id: ID! }  # name mancante
    type Query { a: A }
    """
    )
    code, out = run_diff(mirror, backend)
    data = json.loads(out)
    assert code == 1
    assert data["classification"] in ("breaking", "mixed")
    # Deve contenere almeno una rottura per Named
    assert any("Named" in x for x in data["interface_breaks"]["A"])


def test_enum_value_with_inline_deprecation_only() -> None:
    mirror = _wrap(
        """
    enum E { A B }
    type Query { _q: String }
    """
    )
    backend = _wrap(
        """
    enum E { A B @deprecated(reason: "legacy") }
    type Query { _q: String }
    """
    )
    code, out = run_diff(mirror, backend)
    data = json.loads(out)
    # Nessun nuovo valore, nessuna rimozione -> aligned
    assert code == 0
    assert data["classification"] in ("aligned",)  # considerato neutro
