"""Nutrition domain models.

Modelli centrali per calcoli nutrizionali, TDEE/BMR, target macro,
profili categoria e aggregazioni giornaliere.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict
import datetime


class GoalStrategy(str, Enum):
    """Strategia nutrizionale utente."""

    CUT = "CUT"  # Deficit calorico
    MAINTAIN = "MAINTAIN"  # Mantenimento peso
    BULK = "BULK"  # Surplus calorico


class ActivityLevel(str, Enum):
    """Livello attività per calcolo TDEE."""

    SEDENTARY = "SEDENTARY"  # 1.2
    LIGHTLY_ACTIVE = "LIGHTLY_ACTIVE"  # 1.375
    MODERATELY_ACTIVE = "MODERATELY_ACTIVE"  # 1.55
    VERY_ACTIVE = "VERY_ACTIVE"  # 1.725
    EXTREMELY_ACTIVE = "EXTREMELY_ACTIVE"  # 1.9


@dataclass(slots=True, frozen=True)
class UserPhysicalData:
    """Dati fisici utente per calcoli metabolici."""

    age: int
    weight_kg: float
    height_cm: float
    sex: str  # "male" | "female"
    activity_level: ActivityLevel


@dataclass(slots=True, frozen=True)
class MacroTargets:
    """Target macro giornalieri calcolati."""

    calories: int
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: Optional[float] = None

    def to_dict(self) -> Dict[str, float]:
        """Convert to dict for serialization."""
        return {
            "calories": self.calories,
            "protein_g": self.protein_g,
            "carbs_g": self.carbs_g,
            "fat_g": self.fat_g,
            "fiber_g": self.fiber_g or 0.0,
        }


@dataclass(slots=True)
class NutritionPlan:
    """Piano nutrizionale utente completo."""

    user_id: str
    strategy: GoalStrategy
    macro_targets: MacroTargets
    physical_data: UserPhysicalData
    bmr: float
    tdee: float
    updated_at: datetime.datetime

    # Parametri personalizzazione
    protein_per_kg: Optional[float] = None  # Override default 1.6-2.2g/kg
    fat_percentage: Optional[float] = None  # Override default 25-30%


@dataclass(slots=True, frozen=True)
class NutrientValues:
    """Valori nutrizionali standard (per 100g base)."""

    calories: Optional[float] = None
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fat: Optional[float] = None
    fiber: Optional[float] = None
    sugar: Optional[float] = None
    sodium: Optional[float] = None

    def scale_to_quantity(self, quantity_g: float) -> "NutrientValues":
        """Scala valori alla quantità specifica."""
        factor = quantity_g / 100.0
        return NutrientValues(
            calories=self.calories * factor if self.calories else None,
            protein=self.protein * factor if self.protein else None,
            carbs=self.carbs * factor if self.carbs else None,
            fat=self.fat * factor if self.fat else None,
            fiber=self.fiber * factor if self.fiber else None,
            sugar=self.sugar * factor if self.sugar else None,
            sodium=self.sodium * factor if self.sodium else None,
        )

    def is_calories_consistent(self, tolerance_pct: float = 0.15) -> bool:
        """Verifica consistenza calorie vs macro (4/4/9 kcal/g)."""
        if not self.calories or not any([self.protein, self.carbs, self.fat]):
            return True

        p = self.protein or 0.0
        c = self.carbs or 0.0
        f = self.fat or 0.0
        calculated_kcal = p * 4 + c * 4 + f * 9

        delta = abs(calculated_kcal - self.calories)
        return (delta / self.calories) <= tolerance_pct

    def recompute_calories(self) -> Optional[float]:
        """Ricalcola calorie da macro (protein+carbs=4kcal/g, fat=9)."""
        if not any([self.protein, self.carbs, self.fat]):
            return self.calories

        p = self.protein or 0.0
        c = self.carbs or 0.0
        f = self.fat or 0.0
        return round(p * 4 + c * 4 + f * 9, 1)


@dataclass(slots=True)
class DailyNutritionSummary:
    """Aggregazione nutrizionale giornaliera."""

    user_id: str
    date: str  # YYYY-MM-DD format

    # Intake totals
    total_nutrients: NutrientValues
    meal_count: int

    # Activity data
    activity_steps: int
    activity_calories_out: float
    # Calculated metrics
    calories_deficit: int  # calories_out - calories_in
    calories_replenished_percent: int  # (in/out) * 100

    # Target comparison (requires NutritionPlan)
    target_adherence: Optional[Dict[str, float]] = None
    macro_balance_score: Optional[float] = None


@dataclass(slots=True, frozen=True)
class CategoryProfile:
    """Profilo nutrizionale per categoria alimento."""

    name: str
    nutrients_per_100g: NutrientValues
    is_garnish: bool = False
    hard_constraints: Optional[Dict[str, float]] = None  # lean_fish carbs=0

    def apply_to_quantity(self, quantity_g: float) -> NutrientValues:
        """Applica profilo alla quantità specifica."""
        return self.nutrients_per_100g.scale_to_quantity(quantity_g)


__all__ = [
    "GoalStrategy",
    "ActivityLevel",
    "UserPhysicalData",
    "MacroTargets",
    "NutritionPlan",
    "NutrientValues",
    "DailyNutritionSummary",
    "CategoryProfile",
]
