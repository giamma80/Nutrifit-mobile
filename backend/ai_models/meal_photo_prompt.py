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

# Dizionari hard-coded rimossi - ora deleghiamo tutto al sistema USDA + LLM intelligente


@dataclass(slots=True)
class ParsedItem:
    label: str  # Nome alimento in inglese (per USDA lookup)
    quantity_g: float
    confidence: float
    calories: int
    source_density: str
    display_name: Optional[str] = None  # Nome per display utente (italiano)


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


def generate_prompt_v3(*, locale: str = "it") -> str:
    """
    Prompt versione 3 - INTELLIGENTE con etichette inglesi per USDA lookup.

    """
    return (
        " COMPITO:"
        " Analizza immagine e valuta di che cibo si tratta "
        " se trovi il dettaglio giusto identifica meglio di quale ricetta "
        "se possibile piatto unico o una ricetta complessa."
        " Se possibile, cerca di identificare il piatto esatto"
        " (es: spaghetti alla carbonara, insalata mista, petto di pollo arrosto, ecc) "
        "e usa questo come display_name per l'utente. "
        " Se non riesci a identificare il piatto, usa il nome generico dell'alimento "
        "(es: pollo, riso, pasta, mela, ecc). cerca di capire gli ingredienti principali "
        "e le quantità."
        " Successivamente nel tuo ragionamento genera etichette alimenti in inglese "
        "(singola parola) per ottimizzare lookup USDA, mantenendo display_name "
        "italiano per l'utente."
        " MUST: restituisci SOLO JSON valido UTF-8 con schema esatto "
        '{"dish_title":"<nome piatto italiano>","items":['
        '{"label":"<english_food_name>","display_name":"<nome italiano>",'
        '"quantity":{"value":<num>,"unit":"g|piece"},"confidence":<0-1>}]}.'
        " DO_NOT: aggiungere testo extra, spiegazioni, markdown, code fences."
        " REGOLE CRITICHE:"
        " 1. dish_title: nome del piatto in italiano per l'utente"
        " 2. label: SEMPRE inglese, preferibilmente una parola, usa nomenclatura "
        "USDA (es: eggs non egg, chicken non poultry, beef non meat). "
        "Se necessario usa due parole per parti specifiche o preparazioni: "
        "egg white, egg whole, chicken breast, chicken thigh, potato boiled, "
        "potato fried, tomato sauce"
        " 3. display_name: nome italiano dell'alimento (es: pollo, riso, pasta "
        "o se possibile pollo arrosto, spaghetti alla carbonara, panino con "
        "prosciutto)"
        " 4. Max 5 items; confidence 0-1; quantity.unit 'g' o 'piece'"
        " 5. Per alimenti usa la forma base USDA quando generico: egg=eggs, "
        "tomato=tomatoes, ma specifica quando necessario: egg white, "
        "chicken breast"
        ' 6. Se nessun cibo: {"dish_title":"","items":[]}'
        " ESEMPI label USDA corretti: eggs, chicken, beef, pork, salmon, "
        "tuna, rice, pasta, bread, cheese, milk, tomatoes, apples, bananas, "
        "broccoli, spinach, potatoes, onions"
    )


def generate_fallback_prompt() -> str:
    return (
        'Riprova. SOLO JSON: {"items":[{"label":"<cibo>",'  # noqa: E501
        '"quantity":{"value":<num>,"unit":"g"},"confidence":<0-1>}]}'
        " Max 5 items. Nessun testo extra."
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
    """
    Densità semplificata - ora deleghiamo tutto al NutrientEnrichmentService.
    Questa funzione rimane solo per compatibilità legacy durante parsing.
    """
    return DEFAULT_DENSITY_KCAL_100G, "temporary"


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
        # Peso medio generico per "piece" - deleghiamo al sistema USDA per precisione
        grams = 100.0  # Valore generico, verrà corretto dal NutrientEnrichmentService
        return float(value) * grams
    return None


def _clamp_quantity(q: float) -> Tuple[float, bool]:
    if q < 0:
        return 0.0, True
    if q > MAX_QUANTITY_G:
        return MAX_QUANTITY_G, True
    return q, False


def parse_and_validate_v3(raw_text: str) -> Tuple[str, List[ParsedItem]]:
    """
    Parser per formato v3 con dish_title e label inglesi.

    Returns:
        Tuple[dish_title, parsed_items]
    """
    data = _safe_json_extract(raw_text)

    # Estrai titolo piatto
    dish_title = data.get("dish_title", "")

    # Estrai items
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

        # Estrai dati base
        label_raw = raw.get("label")  # Inglese per USDA
        display_name_raw = raw.get("display_name")  # Italiano per UI
        quantity_obj = raw.get("quantity")
        confidence_raw = raw.get("confidence", 0.5)

        if not isinstance(label_raw, str) or not label_raw.strip():
            continue
        if not isinstance(confidence_raw, (int, float)):
            continue

        # Normalizza etichette
        label = _normalize_label(label_raw)
        display_name = _normalize_label(display_name_raw) if display_name_raw else label

        # Processa quantità
        q_grams = _convert_quantity(quantity_obj)
        if q_grams is None:
            continue
        q_final, was_clamped = _clamp_quantity(q_grams)

        # Calcola density e calorie (temporaneo - sarà sostituito da enrichment)
        density, src_density = _resolve_density(display_name)  # Usa display_name per euristica
        calories = int(density * q_final / 100.0)

        parsed.append(
            ParsedItem(
                label=label,  # Inglese per USDA lookup
                quantity_g=q_final,
                confidence=float(confidence_raw),
                calories=calories,
                source_density=src_density,
                display_name=display_name,  # Italiano per UI
            )
        )

    return dish_title, parsed


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
    "generate_prompt_v3",
    "generate_fallback_prompt",
    "parse_and_validate",
    "parse_and_validate_with_stats",
    "parse_and_validate_v3",
    "ParsedItem",
    "ParseStats",
    "ParseError",
]
