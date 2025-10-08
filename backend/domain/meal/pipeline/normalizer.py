"""Meal normalization pipeline (Phase 2.1).

Domain service per normalizzazione automatica dei dati nutrizionali
estratti dall'analisi delle foto. Responsabilità:

* Normalizzare label grezze → categoria canonicale
* Applicare garnish clamp (range tipico 5–10g)
* Applicare hard constraints macro (es. lean_fish / poultry carbs=0)
* Calcolare consistenza calorie vs macro (ricalcolo se delta >15%)

Modalità controllo (flag env AI_NORMALIZATION_MODE):
  off      → nessuna azione
  dry_run  → calcola correzioni ma non muta i record (ritorna metadata)
  enforce  → applica mutazioni (clamp garnish, macro fix, calorie recompute)

Il modulo è domain-pure: nessuna dipendenza da infrastructure.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Tuple, List
import re
import logging


# ---- Domain Models ----


@dataclass(slots=True)
class NormalizedMealItem:
    """Item nutrizionale normalizzato per analisi meal photo."""

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


@dataclass(slots=True)
class NormalizationResult:
    """Risultato dell'operazione di normalizzazione."""

    items: List[NormalizedMealItem]
    corrections: int
    garnish_clamped: int
    macro_recomputed: int
    mode: str  # off|dry_run|enforce


# ---- Category Profiles (macro per 100g) ----

CATEGORY_PROFILES: Dict[str, Dict[str, float]] = {
    # valori sugar/sodium indicativi (g per 100g) – fine tuning futuro
    "lean_fish": {
        "protein": 22.0,
        "carbs": 0.0,
        "fat": 2.0,
        "fiber": 0.0,
        "sugar": 0.0,
        "sodium": 0.05,
    },
    "poultry": {
        "protein": 25.0,
        "carbs": 0.0,
        "fat": 4.0,
        "fiber": 0.0,
        "sugar": 0.0,
        "sodium": 0.07,
    },
    "pasta_cooked": {
        "protein": 5.0,
        "carbs": 30.0,
        "fat": 1.5,
        "fiber": 2.0,
        "sugar": 1.0,
        "sodium": 0.01,
    },
    "rice_cooked": {
        "protein": 3.0,
        "carbs": 28.0,
        "fat": 0.5,
        "fiber": 0.5,
        "sugar": 0.1,
        "sodium": 0.0,
    },
    "legume": {
        "protein": 8.0,
        "carbs": 20.0,
        "fat": 1.0,
        "fiber": 6.0,
        "sugar": 3.0,
        "sodium": 0.01,
    },
    "tuber": {
        "protein": 2.0,
        "carbs": 17.0,
        "fat": 0.1,
        "fiber": 2.0,
        "sugar": 1.0,
        "sodium": 0.01,
    },
    "leafy_salad": {
        "protein": 2.0,
        "carbs": 3.0,
        "fat": 0.3,
        "fiber": 2.5,
        "sugar": 0.8,
        "sodium": 0.02,
    },
    "dairy_basic": {
        "protein": 3.5,
        "carbs": 5.0,
        "fat": 3.5,
        "fiber": 0.0,
        "sugar": 5.0,
        "sodium": 0.05,
    },
    "citrus_garnish": {
        "protein": 1.0,
        "carbs": 9.0,
        "fat": 0.2,
        "fiber": 2.0,
        "sugar": 2.0,
        "sodium": 0.0,
    },
    "herb": {
        "protein": 3.0,
        "carbs": 7.0,
        "fat": 0.6,
        "fiber": 4.0,
        "sugar": 0.5,
        "sodium": 0.02,
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


# ---- Pipeline Operations ----


def normalize_label(raw: str) -> str:
    """Normalizza label grezza per classificazione categoria."""
    s = raw.strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


def classify_category(label: str) -> Optional[str]:
    """Classifica categoria nutrizionale da label normalizzata."""
    for pattern, cat in TOKEN_MAP.items():
        if re.search(pattern, label):
            return cat
    return None


def garnish_clamp(quantity_g: float, category: Optional[str]) -> Tuple[float, bool]:
    """Applica clamp quantità per garnish (spezie, erbe, agrumi)."""
    if category in GARNISH_CATEGORIES:
        if quantity_g < GARNISH_MIN_G:
            return GARNISH_MIN_G, True
        if quantity_g > GARNISH_MAX_G:
            return GARNISH_MAX_G, True
    return quantity_g, False


def apply_category_profile(item: NormalizedMealItem) -> None:
    """Applica profilo nutrizionale categoria per macro missing/deboli."""
    if not item.category:
        return
    prof = CATEGORY_PROFILES.get(item.category)
    if not prof:
        return
    factor = item.quantity_g / 100.0 if item.quantity_g else 1.0
    # Regole override:
    # - valore mancante
    # - oppure <30% del profilo
    # - oppure enrichment_source heuristico/default
    weak_factor = 0.3
    allow_override = item.enrichment_source in {None, "heuristic", "default"}

    def need_override(current: Optional[float], key: str) -> bool:
        if current is None:
            return True
        target = prof[key] * factor
        if current < target * weak_factor:
            return True
        return False

    if need_override(item.protein, "protein") or allow_override:
        item.protein = prof["protein"] * factor
    if need_override(item.carbs, "carbs") or allow_override:
        item.carbs = prof["carbs"] * factor
    if need_override(item.fat, "fat") or allow_override:
        item.fat = prof["fat"] * factor
    if need_override(item.fiber, "fiber") or allow_override:
        item.fiber = prof["fiber"] * factor
    # sugar / sodium sempre se mancanti
    if (item.sugar is None) and ("sugar" in prof):
        item.sugar = prof["sugar"] * factor
    if (item.sodium is None) and ("sodium" in prof):
        item.sodium = prof["sodium"] * factor
    item.enrichment_source = "category_profile"


def apply_hard_constraints(item: NormalizedMealItem) -> None:
    """Applica vincoli hard su macro (es. pesce/pollo senza carbs)."""
    if item.category in {"lean_fish", "poultry"} and item.carbs is not None:
        if item.carbs > 2.0:
            item.carbs = 0.0


def recompute_calories(item: NormalizedMealItem) -> Tuple[Optional[float], bool]:
    """Ricalcola calorie da macro (protein+carbs=4kcal/g, fat=9).
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


# ---- Main Pipeline ----

logger = logging.getLogger("domain.meal.normalizer")


class MealNormalizationPipeline:
    """Pipeline per normalizzazione automatica dati meal photo."""

    def __init__(self, debug_enabled: bool = False):
        self.debug_enabled = debug_enabled

    def normalize(
        self,
        *,
        items: List[NormalizedMealItem],
        mode: str,
    ) -> NormalizationResult:
        """Esegue normalizzazione secondo modalità specificata."""
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
        work: List[NormalizedMealItem] = [item for item in items]

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
                if self.debug_enabled:
                    try:
                        logger.info(
                            "macro.override",
                            extra={
                                "label": it.label,
                                "category": it.category,
                                "before": {
                                    "protein": before_macro[0],
                                    "carbs": before_macro[1],
                                    "fat": before_macro[2],
                                    "fiber": before_macro[3],
                                },
                                "after": {
                                    "protein": after_macro[0],
                                    "carbs": after_macro[1],
                                    "fat": after_macro[2],
                                    "fiber": after_macro[3],
                                },
                                "garnish_clamped": it.garnish_clamped,
                            },
                        )
                    except Exception:  # pragma: no cover - logging best effort
                        pass

            # Hard constraints
            before_carbs = it.carbs
            apply_hard_constraints(it)
            if before_carbs != it.carbs:
                corrections += 1
                if self.debug_enabled:
                    try:
                        logger.info(
                            "carbs.hard_constraint",
                            extra={
                                "label": it.label,
                                "category": it.category,
                                "from": before_carbs,
                                "to": it.carbs,
                            },
                        )
                    except Exception:  # pragma: no cover
                        pass

            # Recompute calories
            old_cal = it.calories
            new_cal, corrected = recompute_calories(it)
            if corrected:
                macro_recomp += 1
                if mode == "enforce":
                    it.calories = new_cal
                it.calorie_corrected = True
                if self.debug_enabled:
                    try:
                        logger.info(
                            "calories.corrected",
                            extra={
                                "label": it.label,
                                "category": it.category,
                                "old_calories": old_cal,
                                "new_calories": new_cal,
                                "protein": it.protein,
                                "carbs": it.carbs,
                                "fat": it.fat,
                                "quantity_g": it.quantity_g,
                            },
                        )
                    except Exception:  # pragma: no cover
                        pass

        return NormalizationResult(
            items=work,
            corrections=corrections,
            garnish_clamped=garnish_hits,
            macro_recomputed=macro_recomp,
            mode=mode,
        )


__all__ = [
    "NormalizedMealItem",
    "NormalizationResult",
    "MealNormalizationPipeline",
    "CATEGORY_PROFILES",
]
