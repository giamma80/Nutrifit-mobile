#!/usr/bin/env python
"""Export Strawberry GraphQL schema SDL to backend/graphql/schema.graphql.

Assumes an `app.py` (FastAPI + Strawberry) with `schema` importable via
`import app`. If the module has a top-level `schema` (strawberry.Schema)
it is used; otherwise it tries `app.app.schema`.
"""
from __future__ import annotations
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_PATH = BASE_DIR / "graphql" / "schema.graphql"
print(f"[DEBUG] Export base dir: {BASE_DIR}")
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

try:
    import importlib
    # expects module app with: app: FastAPI and/or schema: strawberry.Schema
    mod = importlib.import_module("app")
    schema = getattr(mod, "schema", None)
    if schema is None:
        # Try attribute on FastAPI app
        app_obj = getattr(mod, "app", None)
        schema = getattr(app_obj, "schema", None)
    if schema is None:
        print(
            "[ERROR] Schema not found (need 'schema' or 'app.schema').",
            file=sys.stderr,
        )
        sys.exit(2)
    try:
        sdl = schema.as_str()
    except Exception:
        from strawberry.printer import print_schema
        sdl = print_schema(schema)
    print(f"[DEBUG] SDL size: {len(sdl)} chars")
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        f.write(sdl)
        f.flush()
        os_path = str(OUT_PATH)
    print(f"[INFO] Wrote SDL → {OUT_PATH} (exists={OUT_PATH.exists()})")
except ModuleNotFoundError as e:
    print(f"[ERROR] Cannot import app module: {e}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"[ERROR] Unexpected failure exporting schema: {e}", file=sys.stderr)
    sys.exit(3)
