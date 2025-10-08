"""Category profile adapter - migrates rules/category_profiles.py logic.

Implementa CategoryProfilePort con la logica esistente di classificazione,
garnish clamp, category profiles, e hard constraints.
"""

from __future__ import annotations

import re
from typing import Optional, Dict, Tuple

from domain.nutrition.model import CategoryProfile, NutrientValues
from domain.nutrition.ports import CategoryProfilePort


# Migrated from rules/category_profiles.py
CATEGORY_PROFILES_DATA = {
    "lean_fish": {
        "protein": 22.0,
        "carbs": 0.0,  # hard constraint
        "fat": 2.0,
        "fiber": 0.0,
        "sugar": 0.0,
        "sodium": 0.06,
    },
    "poultry": {
        "protein": 25.0,
        "carbs": 0.0,  # hard constraint
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
        "sodium": 0.006,
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
    r"patate?|potato": "tuber",
    r"lattuga|insalata|lettuce|spinach|kale": "leafy_salad",
    r"latte|milk|yogurt": "dairy_basic",
    r"limone|lemon|lime|orange|agrume": "citrus_garnish",
    r"prezzemolo|parsley|basil|basilico|erba|herb": "herb",
}


class CategoryProfileAdapter(CategoryProfilePort):
    """Adapter per category profiles con logica migrata da rules/."""

    def __init__(self) -> None:
        self._profiles: Dict[str, CategoryProfile] = {}
        self._initialize_profiles()

    def _initialize_profiles(self) -> None:
        """Inizializza profiles da CATEGORY_PROFILES_DATA."""
        for name, data in CATEGORY_PROFILES_DATA.items():
            nutrients = NutrientValues(
                calories=None,  # Will be computed from macros
                protein=data["protein"],
                carbs=data["carbs"],
                fat=data["fat"],
                fiber=data["fiber"],
                sugar=data["sugar"],
                sodium=data["sodium"],
            )

            # Hard constraints per lean_fish/poultry (carbs=0)
            hard_constraints = None
            if name in ["lean_fish", "poultry"]:
                hard_constraints = {"carbs": 0.0}

            self._profiles[name] = CategoryProfile(
                name=name,
                nutrients_per_100g=nutrients,
                is_garnish=name in GARNISH_CATEGORIES,
                hard_constraints=hard_constraints,
            )

    def get_profile(self, category: str) -> Optional[CategoryProfile]:
        """Recupera profilo per categoria."""
        return self._profiles.get(category)

    def get_all_profiles(self) -> Dict[str, CategoryProfile]:
        """Recupera tutti i profili."""
        return self._profiles.copy()

    def classify_food(self, food_label: str) -> Optional[str]:
        """Classifica alimento in categoria usando TOKEN_MAP."""
        normalized = self._normalize_label(food_label)

        for pattern, category in TOKEN_MAP.items():
            if re.search(pattern, normalized):
                return category

        return None

    def _normalize_label(self, raw: str) -> str:
        """Normalizza label per classificazione."""
        s = raw.strip().lower()
        s = re.sub(r"\s+", " ", s)
        return s

    def apply_garnish_clamp(
        self,
        quantity_g: float,
        category: Optional[str],
    ) -> Tuple[float, bool]:
        """Applica clamp garnish 5-10g se categoria garnish."""
        if not category:
            return quantity_g, False

        profile = self.get_profile(category)
        if not profile or not profile.is_garnish:
            return quantity_g, False

        if quantity_g < GARNISH_MIN_G:
            return GARNISH_MIN_G, True
        if quantity_g > GARNISH_MAX_G:
            return GARNISH_MAX_G, True

        return quantity_g, False


__all__ = ["CategoryProfileAdapter"]
