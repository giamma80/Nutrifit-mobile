#!/usr/bin/env python
"""Export Strawberry GraphQL schema SDL.

Default output: backend/graphql/schema.graphql
Override path: --out <path>

Assumes `app.py` exposes either `schema` (strawberry.Schema) or `app.schema`.
Exit codes:
 0 success
 1 import failure
 2 schema attribute not found
 3 unexpected error
"""
from __future__ import annotations
import sys
from pathlib import Path
import argparse

BASE_DIR = Path(__file__).resolve().parent.parent
# Ensure backend root (BASE_DIR) is on sys.path for 'import app'
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
DEFAULT_OUT = BASE_DIR / "graphql" / "schema.graphql"

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("--out", dest="out", default=str(DEFAULT_OUT))
parser.add_argument("-h", "--help", action="help")
args = parser.parse_args()
OUT_PATH = Path(args.out).resolve()
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
    OUT_PATH.write_text(sdl, encoding="utf-8")
    print(f"[INFO] schema SDL written to {OUT_PATH}")
except ModuleNotFoundError as e:
    print(f"[ERROR] Cannot import app module: {e}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"[ERROR] Unexpected failure exporting schema: {e}", file=sys.stderr)
    sys.exit(3)
