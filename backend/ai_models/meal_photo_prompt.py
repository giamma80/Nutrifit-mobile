"""Prompt & Parsing utilities per Meal Photo Analysis (Fase 1 GPT-4V)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import json
import re

MAX_ITEMS = 5
MAX_QUANTITY_G = 2000.0
DEFAULT_DENSITY_KCAL_100G = 100.0

# Versione prompt corrente (incrementare quando cambia lo schema / istruzioni).
PROMPT_VERSION = 2  # incrementato dopo introduzione prompt v2 più restrittivo

DENSITY_MAP = {
    "pollo": 165.0,
    "petto di pollo": 165.0,
    "insalata": 20.0,
    "insalata mista": 20.0,
    "riso": 350.0,
    "pasta": 360.0,
    "mela": 52.0,
    "banana": 89.0,
    "acqua": 0.0,
}

PIECE_AVG_WEIGHT_G = {"mela": 150.0, "banana": 120.0}


@dataclass(slots=True)
class ParsedItem:
    label: str
    quantity_g: float
    confidence: float
    calories: int
    source_density: str


@dataclass(slots=True)
class ParseStats:
    success: bool
    items_count: int
    clamped_count: int
    prompt_version: int
    raw_error: Optional[str] = None


class ParseError(Exception):
    pass


def generate_prompt(*, locale: str = "it") -> str:
    parts = [
        "Analizza la foto del pasto e restituisci SOLO JSON valido: ",
        '{"items":[',
        '{"label":"string",',
        '"quantity":{"value":<num>,"unit":"g|piece"},',
        '"confidence":<0-1>',
        "]}.",
        " Regole: max 5 items, label brevi in italiano. ",
        'Se nessun riconoscimento: {"items": []}.',
    ]
    return "".join(parts)


def generate_prompt_v2(*, locale: str = "it") -> str:
    """Prompt versione 2 con regole più esplicite e MUST/DO_NOT per il modello.

    Non sostituisce ancora il prompt legacy; usato in sperimentazione
    controllata.
    """
    return (
        "MUST: restituisci SOLO JSON valido UTF-8 con schema esatto "
        '{"items":[{"label":"string","quantity":'
        '{"value":<num>,"unit":"g|piece"},"confidence":<0-1>}]}.'
        " DO_NOT: aggiungere testo extra, spiegazioni, markdown, code fences."  # noqa: E501
        " Regole: max 5 items; label concise in italiano minuscolo; "
        'se nessun cibo: {"items": []}. '
        " quantity.unit deve essere 'g' oppure 'piece'; se 'piece' value è numero pezzi (interi o decimali)"  # noqa: E501
        " confidence compreso tra 0 e 1."
    )


def generate_fallback_prompt() -> str:
    return (
        'Riprova. SOLO JSON: {"items":[{"label":"<cibo>",'  # noqa: E501
        '"quantity":{"value":<num>,"unit":"g"},"confidence":<0-1>}]}'
        " Max 3 items. Nessun testo extra."
    )


def _safe_json_extract(text: str) -> Dict[str, Any]:
    first = text.find("{")
    last = text.rfind("}")
    if first == -1 or last == -1 or last <= first:
        raise ParseError("NO_JSON_OBJECT")
    snippet = text[first : last + 1]
    try:
        obj = json.loads(snippet)
        if not isinstance(obj, dict):
            raise ParseError("ROOT_NOT_OBJECT")
        return obj
    except Exception as exc:  # pragma: no cover
        raise ParseError(f"INVALID_JSON: {exc}") from exc


def _normalize_label(raw: str) -> str:
    lab = raw.strip().lower()
    lab = re.sub(r"[^a-zàèéìòóùA-Z0-9 ]", "", lab)
    lab = re.sub(r"\s+", " ", lab).strip()
    return lab


def _resolve_density(label: str) -> Tuple[float, str]:
    if label in DENSITY_MAP:
        return DENSITY_MAP[label], "map"
    if any(k in label for k in ["insalata", "verdura"]):
        return 20.0, "heuristic"
    if any(k in label for k in ["pollo", "carne", "petto"]):
        return 165.0, "heuristic"
    if any(k in label for k in ["riso", "pasta", "cereale"]):
        return 350.0, "heuristic"
    if any(k in label for k in ["mela", "frutta", "banana"]):
        return 60.0, "heuristic"
    return DEFAULT_DENSITY_KCAL_100G, "fallback"


def _convert_quantity(quantity_obj: Any) -> Optional[float]:
    if not isinstance(quantity_obj, dict):
        return None
    value = quantity_obj.get("value")
    unit = quantity_obj.get("unit")
    if not isinstance(value, (int, float)):
        return None
    if unit == "g":
        return float(value)
    if unit == "piece":
        label_hint = quantity_obj.get("label_hint")
        if isinstance(label_hint, str):
            lw = _normalize_label(label_hint)
            grams = PIECE_AVG_WEIGHT_G.get(lw, 100.0)
        else:
            grams = 100.0
        return float(value) * grams
    return None


def _clamp_quantity(q: float) -> Tuple[float, bool]:
    if q < 0:
        return 0.0, True
    if q > MAX_QUANTITY_G:
        return MAX_QUANTITY_G, True
    return q, False


def parse_and_validate(raw_text: str) -> List[ParsedItem]:
    data = _safe_json_extract(raw_text)
    items_raw = data.get("items")
    if items_raw is None:
        raise ParseError("MISSING_ITEMS_ARRAY")
    if not isinstance(items_raw, list):
        raise ParseError("ITEMS_NOT_LIST")
    parsed: List[ParsedItem] = []
    for raw in items_raw:
        if len(parsed) >= MAX_ITEMS:
            break
        if not isinstance(raw, dict):
            continue
        label_raw = raw.get("label")
        quantity_obj = raw.get("quantity")
        confidence_raw = raw.get("confidence")
        if not isinstance(label_raw, str):
            continue
        label_norm = _normalize_label(label_raw)
        q = _convert_quantity(quantity_obj)
        if q is None:
            continue
        q, _ = _clamp_quantity(q)
        if not isinstance(confidence_raw, (int, float)):
            confidence = 0.5
        else:
            confidence = float(confidence_raw)
        if confidence < 0 or confidence > 1:
            confidence = max(0.0, min(1.0, confidence))
        density, density_src = _resolve_density(label_norm)
        calories = int(round(q * density / 100.0))
        parsed.append(
            ParsedItem(
                label=label_norm,
                quantity_g=q,
                confidence=confidence,
                calories=calories,
                source_density=density_src,
            )
        )
    return parsed


def parse_and_validate_with_stats(
    raw_text: str,
) -> Tuple[List[ParsedItem], ParseStats]:
    """Wrapper non invasivo che arricchisce parse con statistiche.

    Non modifica la logica di parsing esistente; cattura eventuali errori e
    restituisce lista vuota + stats con success False. Usato per metriche.
    """
    clamped_total = 0
    try:
        data = _safe_json_extract(raw_text)
        items_raw = data.get("items")
        if items_raw is None:
            raise ParseError("MISSING_ITEMS_ARRAY")
        if not isinstance(items_raw, list):
            raise ParseError("ITEMS_NOT_LIST")
        parsed: List[ParsedItem] = []
        for raw in items_raw:
            if len(parsed) >= MAX_ITEMS:
                break
            if not isinstance(raw, dict):
                continue
            label_raw = raw.get("label")
            quantity_obj = raw.get("quantity")
            confidence_raw = raw.get("confidence")
            if not isinstance(label_raw, str):
                continue
            label_norm = _normalize_label(label_raw)
            q = _convert_quantity(quantity_obj)
            if q is None:
                continue
            q_clamped, was_clamped = _clamp_quantity(q)
            if was_clamped:
                clamped_total += 1
            q = q_clamped
            if not isinstance(confidence_raw, (int, float)):
                confidence = 0.5
            else:
                confidence = float(confidence_raw)
            if confidence < 0 or confidence > 1:
                confidence = max(0.0, min(1.0, confidence))
            density, density_src = _resolve_density(label_norm)
            calories = int(round(q * density / 100.0))
            parsed.append(
                ParsedItem(
                    label=label_norm,
                    quantity_g=q,
                    confidence=confidence,
                    calories=calories,
                    source_density=density_src,
                )
            )
        stats = ParseStats(
            success=True,
            items_count=len(parsed),
            clamped_count=clamped_total,
            prompt_version=PROMPT_VERSION,
        )
        return parsed, stats
    except ParseError as exc:
        stats = ParseStats(
            success=False,
            items_count=0,
            clamped_count=0,
            prompt_version=PROMPT_VERSION,
            raw_error=str(exc),
        )
        return [], stats


__all__ = [
    "generate_prompt",
    "generate_prompt_v2",
    "generate_fallback_prompt",
    "parse_and_validate",
    "parse_and_validate_with_stats",
    "ParsedItem",
    "ParseStats",
    "ParseError",
]
