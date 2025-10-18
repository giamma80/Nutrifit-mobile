"""Nutrition calculation service - core domain logic.

Responsabilità:
- Calcoli BMR/TDEE basati su età, peso, altezza, sesso, attività
- Determinazione target macro personalizzati per strategia nutrizionale
- Recompute calorie da macro (4/4/9 kcal/g) con validazione consistenza
- Aggregazione daily nutrition summary con deficit/surplus calorico
- Applicazione category profiles per enrichment nutrizionale
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple
from datetime import datetime

from domain.nutrition.model import (
    NutritionPlan,
    MacroTargets,
    UserPhysicalData,
    ActivityLevel,
    GoalStrategy,
    NutrientValues,
    DailyNutritionSummary,
)
from domain.nutrition.ports import (
    NutritionPlanPort,
    MealDataPort,
    ActivityDataPort,
    CategoryProfilePort,
)


logger = logging.getLogger("domain.nutrition.calculation")


class NutritionCalculationService:
    """Core service per calcoli nutrizionali e aggregazioni."""

    def __init__(
        self,
        nutrition_plan_port: NutritionPlanPort,
        meal_data_port: MealDataPort,
        activity_data_port: ActivityDataPort,
        category_profile_port: CategoryProfilePort,
    ):
        self.nutrition_plan_port = nutrition_plan_port
        self.meal_data_port = meal_data_port
        self.activity_data_port = activity_data_port
        self.category_profile_port = category_profile_port

    def calculate_bmr(self, physical_data: UserPhysicalData) -> float:
        """Calcola BMR usando formula Mifflin-St Jeor.

        Maschi: BMR = 10 × peso + 6.25 × altezza - 5 × età + 5
        Femmine: BMR = 10 × peso + 6.25 × altezza - 5 × età - 161
        """
        base = 10 * physical_data.weight_kg + 6.25 * physical_data.height_cm - 5 * physical_data.age

        if physical_data.sex.lower() == "male":
            return base + 5
        else:  # female
            return base - 161

    def calculate_tdee(self, bmr: float, activity_level: ActivityLevel) -> float:
        """Calcola TDEE applicando moltiplicatore attività al BMR."""
        multipliers = {
            ActivityLevel.SEDENTARY: 1.2,
            ActivityLevel.LIGHTLY_ACTIVE: 1.375,
            ActivityLevel.MODERATELY_ACTIVE: 1.55,
            ActivityLevel.VERY_ACTIVE: 1.725,
            ActivityLevel.EXTREMELY_ACTIVE: 1.9,
        }

        multiplier = multipliers.get(activity_level, 1.2)
        return bmr * multiplier

    def calculate_macro_targets(
        self,
        tdee: float,
        strategy: GoalStrategy,
        physical_data: UserPhysicalData,
        protein_per_kg: Optional[float] = None,
        fat_percentage: Optional[float] = None,
    ) -> MacroTargets:
        """Calcola target macro personalizzati per strategia."""

        # Adjustment calorico per strategia
        calorie_adjustments = {
            GoalStrategy.CUT: -0.20,  # -20% per deficit
            GoalStrategy.MAINTAIN: 0.0,  # mantenimento
            GoalStrategy.BULK: 0.15,  # +15% per surplus controllato
        }

        adjustment = calorie_adjustments.get(strategy, 0.0)
        target_calories = int(round(tdee * (1 + adjustment)))

        # Proteine: default 1.8g/kg, personalizzabile
        protein_per_kg = protein_per_kg or 1.8
        protein_g = physical_data.weight_kg * protein_per_kg

        # Grassi: default 27% delle calorie, personalizzabile
        fat_percentage = fat_percentage or 0.27
        fat_calories = target_calories * fat_percentage
        fat_g = fat_calories / 9  # 9 kcal/g per grassi

        # Carboidrati: resto delle calorie
        protein_calories = protein_g * 4  # 4 kcal/g per proteine
        remaining_calories = target_calories - protein_calories - fat_calories
        carbs_g = max(0, remaining_calories / 4)  # 4 kcal/g per carbs

        # Fibra: approssimazione 14g per 1000kcal
        fiber_g = (target_calories / 1000) * 14

        return MacroTargets(
            calories=target_calories,
            protein_g=round(protein_g, 1),
            carbs_g=round(carbs_g, 1),
            fat_g=round(fat_g, 1),
            fiber_g=round(fiber_g, 1),
        )

    def create_nutrition_plan(
        self,
        user_id: str,
        strategy: GoalStrategy,
        physical_data: UserPhysicalData,
        protein_per_kg: Optional[float] = None,
        fat_percentage: Optional[float] = None,
    ) -> NutritionPlan:
        """Crea piano nutrizionale completo."""

        bmr = self.calculate_bmr(physical_data)
        tdee = self.calculate_tdee(bmr, physical_data.activity_level)

        macro_targets = self.calculate_macro_targets(
            tdee=tdee,
            strategy=strategy,
            physical_data=physical_data,
            protein_per_kg=protein_per_kg,
            fat_percentage=fat_percentage,
        )

        plan = NutritionPlan(
            user_id=user_id,
            strategy=strategy,
            macro_targets=macro_targets,
            physical_data=physical_data,
            bmr=round(bmr, 1),
            tdee=round(tdee, 1),
            updated_at=datetime.now(),
            protein_per_kg=protein_per_kg,
            fat_percentage=fat_percentage,
        )

        return self.nutrition_plan_port.save(plan)

    def recompute_calories_from_macros(
        self,
        nutrients: NutrientValues,
        tolerance_pct: float = 0.15,
    ) -> Tuple[Optional[float], bool]:
        """Ricalcola calorie da macro se inconsistenti.

        Returns:
            (new_calories, was_corrected)
        """
        if not any([nutrients.protein, nutrients.carbs, nutrients.fat]):
            return nutrients.calories, False

        calculated = nutrients.recompute_calories()

        # Se calorie mancanti, usa quelle calcolate
        if nutrients.calories is None:
            return calculated, True

        # Check consistenza esistenti
        if not nutrients.is_calories_consistent(tolerance_pct):
            logger.debug(
                f"Calories inconsistent: {nutrients.calories} vs " f"{calculated}, correcting"
            )
            return calculated, True

        return nutrients.calories, False

    def apply_category_enrichment(
        self,
        nutrients: NutrientValues,
        quantity_g: float,
        category: Optional[str],
        enrichment_source: Optional[str] = None,
    ) -> Tuple[NutrientValues, bool]:
        """Applica enrichment da category profile se nutrients deboli.

        Returns:
            (enriched_nutrients, was_enriched)
        """
        if not category:
            return nutrients, False

        profile = self.category_profile_port.get_profile(category)
        if not profile:
            return nutrients, False

        # Applica solo se missing o fonte heuristic/default
        allow_override = enrichment_source in {None, "heuristic", "default"}
        if not allow_override:
            return nutrients, False

        profile_nutrients = profile.apply_to_quantity(quantity_g)
        enriched = False

        # Costruisci nuovi valori con enrichment selettivo
        new_values = {}
        for field in ["protein", "carbs", "fat", "fiber", "sugar", "sodium"]:
            current = getattr(nutrients, field)
            profile_val = getattr(profile_nutrients, field)

            if current is None and profile_val is not None:
                new_values[field] = profile_val
                enriched = True
            else:
                new_values[field] = current

        # Calorie: usa existing o recompute se missing
        new_values["calories"] = nutrients.calories

        if enriched:
            return NutrientValues(**new_values), True

        return nutrients, False

    def calculate_daily_summary(
        self,
        user_id: str,
        date: str,  # YYYY-MM-DD
    ) -> DailyNutritionSummary:
        """Calcola aggregazione nutrizionale giornaliera completa."""

        # Recupera dati pasti
        meals = self.meal_data_port.get_daily_meals(user_id, date)
        total_nutrients = self.meal_data_port.get_daily_totals(user_id, date)

        # Recupera dati attività
        activity_data = self.activity_data_port.get_daily_activity(user_id, date)
        steps = int(activity_data.get("steps", 0))
        calories_out = activity_data.get("calories_out", 0.0)

        # Calcola metriche deficit/surplus
        calories_in = total_nutrients.calories or 0
        calories_deficit = int(round(calories_out - calories_in))

        if calories_out > 0:
            replenished_pct = (calories_in / calories_out) * 100
            replenished_pct = max(0, min(999, replenished_pct))  # clamp 0-999
        else:
            replenished_pct = 0

        # Target adherence (se piano disponibile)
        target_adherence = None
        plan = self.nutrition_plan_port.get_by_user_id(user_id)
        if plan and total_nutrients.calories and hasattr(plan, "macro_targets"):
            targets = plan.macro_targets
            # Safety check per evitare errori con Mock objects
            if hasattr(targets, "calories") and isinstance(targets.calories, (int, float)):
                target_adherence = {
                    "calories": (calories_in / targets.calories) * 100,
                    "protein": ((total_nutrients.protein or 0) / targets.protein_g) * 100,
                    "carbs": ((total_nutrients.carbs or 0) / targets.carbs_g) * 100,
                    "fat": ((total_nutrients.fat or 0) / targets.fat_g) * 100,
                }

        return DailyNutritionSummary(
            user_id=user_id,
            date=date,
            total_nutrients=total_nutrients,
            meal_count=len(meals),
            activity_steps=steps,
            activity_calories_out=calories_out,
            calories_deficit=calories_deficit,
            calories_replenished_percent=int(round(replenished_pct)),
            target_adherence=target_adherence,
        )


# Service factory
def get_nutrition_service() -> NutritionCalculationService:
    """Factory per nutrition service - sempre abilitato."""
    from domain.nutrition.adapters.nutrition_plan_adapter import (  # noqa
        NutritionPlanAdapter,
    )
    from domain.nutrition.adapters.meal_data_adapter import MealDataAdapter  # noqa
    from domain.nutrition.adapters.activity_adapter import (  # noqa
        ActivityDataAdapter,
    )
    from domain.nutrition.adapters.category_adapter import (  # noqa
        CategoryProfileAdapter,
    )

    return NutritionCalculationService(
        nutrition_plan_port=NutritionPlanAdapter(),
        meal_data_port=MealDataAdapter(),
        activity_data_port=ActivityDataAdapter(),
        category_profile_port=CategoryProfileAdapter(),
    )


__all__ = ["NutritionCalculationService", "get_nutrition_service"]
