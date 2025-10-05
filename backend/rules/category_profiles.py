"""Category profiles & normalization utilities (Phase 2.1).

Responsabilità:
* Normalizzare label grezze → categoria canonicale
* Applicare garnish clamp (range tipico 5–10g)
* Applicare hard constraints macro (es. lean_fish / poultry carbs=0)
* Calcolare consistenza calorie vs macro (ricalcolo se delta >15%)

Modalità controllo (flag env AI_NORMALIZATION_MODE):
  off      → nessuna azione
  dry_run  → calcola correzioni ma non muta i record (ritorna metadata)
  enforce  → applica mutazioni (clamp garnish, macro fix, calorie recompute)

Il modulo è a basso impatto: nessuna dipendenza da FastAPI / GraphQL.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Tuple, List
import re


# ---- Data Structures ----


@dataclass(slots=True)
class NormalizedItem:
    label: str
    quantity_g: float
    calories: Optional[float]
    protein: Optional[float]
    carbs: Optional[float]
    fat: Optional[float]
    fiber: Optional[float]
    sugar: Optional[float] = None
    sodium: Optional[float] = None
    category: Optional[str] = None
    # heuristic|default|category_profile
    enrichment_source: Optional[str] = None
    calorie_corrected: bool = False
    garnish_clamped: bool = False


# ---- Category Profiles (macro per 100g) ----

CATEGORY_PROFILES: Dict[str, Dict[str, float]] = {
    # valori sugar/sodium indicativi (g per 100g) – fine tuning futuro
    "lean_fish": {
        "protein": 22.0, "carbs": 0.0, "fat": 2.0, "fiber": 0.0,
        "sugar": 0.0, "sodium": 0.05,
    },
    "poultry": {
        "protein": 25.0, "carbs": 0.0, "fat": 4.0, "fiber": 0.0,
        "sugar": 0.0, "sodium": 0.07,
    },
    "pasta_cooked": {
        "protein": 5.0, "carbs": 30.0, "fat": 1.5, "fiber": 2.0,
        "sugar": 1.0, "sodium": 0.01,
    },
    "rice_cooked": {
        "protein": 3.0, "carbs": 28.0, "fat": 0.5, "fiber": 0.5,
        "sugar": 0.1, "sodium": 0.0,
    },
    "legume": {
        "protein": 8.0, "carbs": 20.0, "fat": 1.0, "fiber": 6.0,
        "sugar": 3.0, "sodium": 0.01,
    },
    "tuber": {
        "protein": 2.0, "carbs": 17.0, "fat": 0.1, "fiber": 2.0,
        "sugar": 1.0, "sodium": 0.01,
    },
    "leafy_salad": {
        "protein": 2.0, "carbs": 3.0, "fat": 0.3, "fiber": 2.5,
        "sugar": 0.8, "sodium": 0.02,
    },
    "dairy_basic": {
        "protein": 3.5, "carbs": 5.0, "fat": 3.5, "fiber": 0.0,
        "sugar": 5.0, "sodium": 0.05,
    },
    "citrus_garnish": {
        "protein": 1.0, "carbs": 9.0, "fat": 0.2, "fiber": 2.0,
        "sugar": 2.0, "sodium": 0.0,
    },
    "herb": {
        "protein": 3.0, "carbs": 7.0, "fat": 0.6, "fiber": 4.0,
        "sugar": 0.5, "sodium": 0.02,
    },
}

GARNISH_CATEGORIES = {"citrus_garnish", "herb"}

GARNISH_MIN_G = 5.0
GARNISH_MAX_G = 10.0


TOKEN_MAP = {
    r"salmon|tonno|merluzzo|branzino": "lean_fish",
    r"pollo|chicken|petto": "poultry",
    r"pasta|spaghetti|penne": "pasta_cooked",
    r"riso|rice": "rice_cooked",
    r"ceci|fagioli|lenticchie|bean|lentil|chickpea": "legume",
    r"patata|potato": "tuber",
    r"lattuga|insalata|lettuce|spinach|kale": "leafy_salad",
    r"latte|milk|yogurt": "dairy_basic",
    r"limone|lemon|lime|orange|agrume": "citrus_garnish",
    r"prezzemolo|parsley|basil|basilico|erba|herb": "herb",
}


def normalize_label(raw: str) -> str:
    s = raw.strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


def classify_category(label: str) -> Optional[str]:
    for pattern, cat in TOKEN_MAP.items():
        if re.search(pattern, label):
            return cat
    return None


def garnish_clamp(
    quantity_g: float, category: Optional[str]
) -> Tuple[float, bool]:
    if category in GARNISH_CATEGORIES:
        if quantity_g < GARNISH_MIN_G:
            return GARNISH_MIN_G, True
        if quantity_g > GARNISH_MAX_G:
            return GARNISH_MAX_G, True
    return quantity_g, False


def apply_category_profile(item: NormalizedItem) -> None:
    if not item.category:
        return
    prof = CATEGORY_PROFILES.get(item.category)
    if not prof:
        return
    # Se già presenti macro lasciamo invariato (future override policy?)
    factor = item.quantity_g / 100.0 if item.quantity_g else 1.0
    if item.protein is None:
        item.protein = prof["protein"] * factor
    if item.carbs is None:
        item.carbs = prof["carbs"] * factor
    if item.fat is None:
        item.fat = prof["fat"] * factor
    if item.fiber is None:
        item.fiber = prof["fiber"] * factor
    if item.sugar is None and "sugar" in prof:
        item.sugar = prof["sugar"] * factor
    if item.sodium is None and "sodium" in prof:
        item.sodium = prof["sodium"] * factor
    item.enrichment_source = "category_profile"


def apply_hard_constraints(item: NormalizedItem) -> None:
    if item.category in {"lean_fish", "poultry"} and item.carbs is not None:
        if item.carbs > 2.0:
            item.carbs = 0.0


def recompute_calories(item: NormalizedItem) -> Tuple[Optional[float], bool]:
    """Recompute calories from macros (protein+carbs=4kcal/g, fat=9).
    Return (new_calories, corrected?)."""
    if item.protein is None and item.carbs is None and item.fat is None:
        return item.calories, False
    p = item.protein or 0.0
    c = item.carbs or 0.0
    f = item.fat or 0.0
    kcal = p * 4 + c * 4 + f * 9
    if item.calories is None:
        return round(kcal, 1), True
    # Consistency check
    delta = abs(kcal - item.calories)
    if item.calories > 0 and (delta / item.calories) > 0.15:
        return round(kcal, 1), True
    return item.calories, False


@dataclass(slots=True)
class NormalizationResult:
    items: List[NormalizedItem]
    corrections: int
    garnish_clamped: int
    macro_recomputed: int
    mode: str  # off|dry_run|enforce


def normalize(
    *,
    items: List[NormalizedItem],
    mode: str,
) -> NormalizationResult:
    if mode not in {"off", "dry_run", "enforce"}:
        mode = "off"
    corrections = 0
    garnish_hits = 0
    macro_recomp = 0
    if mode == "off":
        return NormalizationResult(
            items=items,
            corrections=0,
            garnish_clamped=0,
            macro_recomputed=0,
            mode=mode,
        )

    # Work on copies if dry_run
    work: List[NormalizedItem] = [i for i in items]
    for it in work:
        it.label = normalize_label(it.label)
        it.category = classify_category(it.label)
        # Garnish clamp
        new_q, clamped = garnish_clamp(it.quantity_g, it.category)
        if clamped:
            if mode == "enforce":
                it.quantity_g = new_q
            it.garnish_clamped = True
            garnish_hits += 1
        # Category profile macro fill
        before_macro = (it.protein, it.carbs, it.fat, it.fiber)
        apply_category_profile(it)
        after_macro = (it.protein, it.carbs, it.fat, it.fiber)
        if before_macro != after_macro:
            corrections += 1
        # Hard constraints
        before_carbs = it.carbs
        apply_hard_constraints(it)
        if before_carbs != it.carbs:
            corrections += 1
        # Recompute calories
        new_cal, corrected = recompute_calories(it)
        if corrected:
            macro_recomp += 1
            if mode == "enforce":
                it.calories = new_cal
            it.calorie_corrected = True
    return NormalizationResult(
        items=work,
        corrections=corrections,
        garnish_clamped=garnish_hits,
        macro_recomputed=macro_recomp,
        mode=mode,
    )


__all__ = [
    "NormalizedItem",
    "NormalizationResult",
    "normalize",
    "CATEGORY_PROFILES",
]
