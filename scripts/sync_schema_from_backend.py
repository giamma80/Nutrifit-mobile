#!/usr/bin/env python3
"""Sync backend exported schema to root mirror.

Strategia:
1. Prova ad importare `backend.app` e leggere `schema` (senza avviare server).
2. Se fallisce, tenta HTTP introspection su URL fornito via --url (opzionale).
3. Scrive SDL in `backend/graphql/schema.graphql` (se export riuscito)
    e copia in `graphql/schema.graphql` (mirror root).
4. Calcola hash SHA1 e stampa summary.

Exit codes:
 0 success
 1 schema non trovato / import fallito e nessuna URL
 2 errore scrittura
 3 introspection fallita
"""
from __future__ import annotations
import sys
import argparse
import json
import hashlib
from pathlib import Path
from typing import Optional

BACKEND_DIR = Path("backend").resolve()
BACKEND_SCHEMA = BACKEND_DIR / "graphql" / "schema.graphql"
ROOT_SCHEMA = Path("graphql") / "schema.graphql"

INTROSPECTION_QUERY = "query IntrospectionQuery { __schema { types { name } } }"


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def export_via_import() -> Optional[str]:
    try:
        sys.path.insert(0, str(BACKEND_DIR))
        import importlib

        mod = importlib.import_module("app")
        schema = getattr(mod, "schema", None)
        if schema is None:
            app_obj = getattr(mod, "app", None)
            schema = getattr(app_obj, "schema", None)
        if schema is None:
            return None
        try:
            return schema.as_str()
        except Exception:  # pragma: no cover
            from strawberry.printer import print_schema  # type: ignore

            return print_schema(schema)
    except Exception:  # pragma: no cover
        return None


def export_via_http(url: str) -> Optional[str]:
    try:
        import httpx  # type: ignore

        q = {"query": INTROSPECTION_QUERY}
        r = httpx.post(url, json=q, timeout=10)
        if r.status_code != 200:
            return None
        # Introspection minimale (reachability). SDL locale preferito.
        return None
    except Exception:  # pragma: no cover
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--url",
        help="Endpoint GraphQL per fallback introspection",
        default=None,
    )
    args = parser.parse_args()

    sdl = export_via_import()
    if sdl is None and args.url:
        _ = export_via_http(args.url)
        sdl = export_via_import()  # ritenta dopo eventuale avvio esterno

    if sdl is None:
        print(
            "[ERROR] Impossibile ottenere schema: import fallito e " "nessun fallback",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        write_file(BACKEND_SCHEMA, sdl)
        write_file(ROOT_SCHEMA, sdl)
    except Exception as e:
        print(f"[ERROR] Scrittura schema fallita: {e}", file=sys.stderr)
        sys.exit(2)

    digest = sha1(sdl)
    summary = {
        "mirror": str(ROOT_SCHEMA),
        "backend": str(BACKEND_SCHEMA),
        "hash": digest,
        "lines": len(sdl.splitlines()),
    }
    print(json.dumps(summary, indent=2))
    sys.exit(0)


if __name__ == "__main__":  # pragma: no cover
    main()
