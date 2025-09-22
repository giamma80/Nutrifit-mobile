#!/usr/bin/env python3

"""Semantic (ridotta) GraphQL schema diff.

UNICUM: questo è l'unico script autorizzato per il diff semantico.

Funzionalità coperte dai test:
* added/removed fields (object types)
* added enum values
* interfacce: campi richiesti mancanti => breaking

Classificazioni: aligned / additive / breaking.
"""

from __future__ import annotations
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, TypedDict

# Percorsi: root/scripts/verify_schema_breaking.py
_REPO_ROOT = Path(__file__).resolve().parent.parent
MIRROR_PATH = _REPO_ROOT / "graphql" / "schema.graphql"
BACKEND_PATH = _REPO_ROOT / "backend" / "graphql" / "schema.graphql"

NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _extract_fields(lines: List[str]) -> Set[str]:
    fields: Set[str] = set()
    pattern = re.compile(r"(\b[A-Za-z_][A-Za-z0-9_]*)\s*:")
    for ln in lines:
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        for name in pattern.findall(ln):
            if NAME_RE.match(name):
                fields.add(name)
    return fields


def _extract_enum_values(lines: List[str]) -> Set[str]:
    vals: Set[str] = set()
    for ln in lines:
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        for tok in re.split(r"[\s,]+", ln):
            if not tok or tok.startswith("@"):
                continue
            if NAME_RE.match(tok):
                vals.add(tok)
    return vals


class ParsedSchema(TypedDict):
    objects: Dict[str, Set[str]]
    interfaces: Dict[str, Set[str]]
    implements: Dict[str, List[str]]
    enums: Dict[str, Set[str]]


def parse_schema(sdl: str) -> ParsedSchema:
    cleaned = []
    for raw in sdl.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if line.strip():
            cleaned.append(line)
    text = "\n".join(cleaned)

    pattern = re.compile(
        r"(type|interface|enum)\s+(\w+)([^\{]*)\{([^}]*)\}",
        re.MULTILINE | re.DOTALL,
    )

    objects: Dict[str, Set[str]] = {}
    interfaces: Dict[str, Set[str]] = {}
    implements: Dict[str, List[str]] = {}
    enums: Dict[str, Set[str]] = {}

    for kind, name, extra, body in pattern.findall(text):
        body_lines = [ln.strip() for ln in body.split("\n") if ln.strip()]
        if kind == "type":
            impls: List[str] = []
            if "implements" in extra:
                after = extra.split("implements", 1)[1]
                impls = [
                    p.strip()
                    for p in re.split(r"[&\s]+", after)
                    if p.strip()
                ]
            objects[name] = _extract_fields(body_lines)
            implements[name] = impls
        elif kind == "interface":
            interfaces[name] = _extract_fields(body_lines)
        elif kind == "enum":
            enums[name] = _extract_enum_values(body_lines)

    for k in list(objects.keys()):
        implements.setdefault(k, [])

    return ParsedSchema(
        objects=objects,
        interfaces=interfaces,
        implements=implements,
        enums=enums,
    )


def main() -> int:
    if not MIRROR_PATH.exists() or not BACKEND_PATH.exists():
        print(json.dumps({
            "error": "File schema mancanti",
            "mirror_exists": MIRROR_PATH.exists(),
            "backend_exists": BACKEND_PATH.exists(),
        }))
        return 2

    mirror_sdl = MIRROR_PATH.read_text(encoding="utf-8")
    backend_sdl = BACKEND_PATH.read_text(encoding="utf-8")

    m = parse_schema(mirror_sdl)
    b = parse_schema(backend_sdl)

    added_fields: Dict[str, List[str]] = {}
    removed_fields: Dict[str, List[str]] = {}
    added_enum_values: Dict[str, List[str]] = {}
    interface_breaks: Dict[str, List[str]] = {}

    for obj, b_fields in b["objects"].items():
        m_fields = m["objects"].get(obj, set())
        add = sorted(b_fields - m_fields)
        rem = sorted(m_fields - b_fields)
        if add:
            added_fields[obj] = add
        if rem:
            removed_fields[obj] = rem

    for enum_name, b_vals in b["enums"].items():
        m_vals = m["enums"].get(enum_name, set())
        add = sorted(b_vals - m_vals)
        if add:
            added_enum_values[enum_name] = add

    for obj, impl_list in b["implements"].items():
        if not impl_list:
            continue
        b_fields = b["objects"].get(obj, set())
        for iface in impl_list:
            iface_fields = (
                b["interfaces"].get(iface)
                or m["interfaces"].get(iface)
                or set()
            )
            missing = sorted(f for f in iface_fields if f not in b_fields)
            if missing:
                msgs = [
                    f"Campo mancante per interfaccia {iface}: {f}"
                    for f in missing
                ]
                interface_breaks.setdefault(obj, []).extend(msgs)

    breaking = bool(removed_fields or interface_breaks)
    additive_changes = bool(added_fields or added_enum_values)

    if breaking:
        classification = "breaking"
    elif additive_changes:
        classification = "additive"
    else:
        classification = "aligned"

    data = {
        "classification": classification,
        "added_fields": added_fields,
        "removed_fields": removed_fields,
        "added_enum_values": added_enum_values,
        "interface_breaks": interface_breaks,
        "tool": "verify_schema_breaking",
        "tool_version": "0.2.0",
    }
    print(json.dumps(data, ensure_ascii=False))
    return 1 if breaking else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
