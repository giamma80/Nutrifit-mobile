"""Integration service for nutrition domain with existing GraphQL layer.

Provides backward-compatible interface while enabling gradual rollout
of new nutrition domain through feature flag AI_NUTRITION_V2.
"""

from __future__ import annotations

import logging
from typing import Optional, Dict, Any

from domain.nutrition.application.nutrition_service import (
    NutritionCalculationService,
    get_nutrition_service,
)
from domain.nutrition.model import (
    UserPhysicalData,
    ActivityLevel,
    MacroTargets,
    NutrientValues,
)

logger = logging.getLogger("domain.nutrition.integration")


class NutritionIntegrationService:
    """Integration layer tra nutrition domain e GraphQL esistente."""

    def __init__(self) -> None:
        self._nutrition_service: NutritionCalculationService

        try:
            self._nutrition_service = get_nutrition_service()
            logger.info("Nutrition domain V2 initialized")
        except Exception as e:
            logger.error(f"Failed to initialize nutrition V2: {e}")
            raise RuntimeError(f"Critical: Nutrition service failed to initialize: {e}")

    def enhanced_daily_summary(
        self,
        user_id: str,
        date: str,
        fallback_summary: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Enhanced daily summary with nutrition domain calculations.

        Args:
            user_id: User identifier
            date: Date in YYYY-MM-DD format
            fallback_summary: Existing summary from app.py logic

        Returns:
            Enhanced summary dict with additional nutrition insights
        """
        try:
            # Calculate enhanced summary using nutrition domain
            domain_summary = self._nutrition_service.calculate_daily_summary(
                user_id=user_id,
                date=date,
            )

            # Merge with existing summary, keeping backward compatibility
            if fallback_summary is not None:
                enhanced = fallback_summary.copy()
            else:
                # Create basic summary structure if no fallback provided
                enhanced = {
                    "date": date,
                    "user_id": user_id,
                    "meals": 0,
                    "calories": 0,
                    "protein": 0.0,
                    "carbs": 0.0,
                    "fat": 0.0,
                    "fiber": 0.0,
                    "sugar": 0.0,
                    "sodium": 0.0,
                    "activity_steps": 0,
                    "activity_calories_out": 0.0,
                    "activity_events": 0,
                    "calories_deficit": 0,
                    "calories_replenished_percent": 0,
                }

            # Add new fields from nutrition domain
            enhanced.update(
                {
                    "nutrition_v2_enabled": True,
                    "target_adherence": domain_summary.target_adherence,
                    "macro_balance_score": domain_summary.macro_balance_score,
                    "enhanced_calculations": {
                        "deficit_v2": domain_summary.calories_deficit,
                        "replenished_pct_v2": domain_summary.calories_replenished_percent,
                    },
                }
            )

            logger.debug(f"Enhanced daily summary for {user_id}/{date}")
            return enhanced

        except Exception as e:
            logger.error(f"Error in enhanced daily summary: {e}")
            # Graceful fallback to existing logic
            if fallback_summary is not None:
                return fallback_summary
            else:
                # Return basic summary if no fallback available
                return {
                    "date": date,
                    "user_id": user_id,
                    "meals": 0,
                    "calories": 0,
                    "protein": 0.0,
                    "carbs": 0.0,
                    "fat": 0.0,
                    "fiber": 0.0,
                    "sugar": 0.0,
                    "sodium": 0.0,
                    "activity_steps": 0,
                    "activity_calories_out": 0.0,
                    "activity_events": 0,
                    "calories_deficit": 0,
                    "calories_replenished_percent": 0,
                }

    def recompute_meal_calories(
        self,
        protein: Optional[float],
        carbs: Optional[float],
        fat: Optional[float],
        existing_calories: Optional[float],
    ) -> tuple[Optional[float], bool]:
        """Enhanced calorie recomputation with nutrition domain.

        Returns:
            (new_calories, was_corrected)
        """
        try:
            nutrients = NutrientValues(
                protein=protein,
                carbs=carbs,
                fat=fat,
                calories=existing_calories,
            )

            return self._nutrition_service.recompute_calories_from_macros(nutrients)

        except Exception as e:
            # Domain V2 error - no fallback available
            import logging

            logger = logging.getLogger("nutrition.integration")
            logger.error(f"Error in nutrition V2 calorie recompute: {e}")
            raise

    def classify_and_enrich_food(
        self,
        food_label: str,
        quantity_g: float,
        existing_nutrients: Dict[str, Any],
    ) -> tuple[Dict[str, Any], Optional[str], bool]:
        """Classify food and apply category enrichment.

        Returns:
            (enriched_nutrients, category, was_enriched)
        """
        try:
            # Classify food using category adapter
            category_adapter = self._nutrition_service.category_profile_port
            category = category_adapter.classify_food(food_label)

            if not category:
                return existing_nutrients, None, False

            # Apply garnish clamp if needed
            adj_quantity, was_clamped = category_adapter.apply_garnish_clamp(quantity_g, category)

            # Convert to domain model for enrichment
            from domain.nutrition.model import NutrientValues

            nutrients = NutrientValues(
                calories=existing_nutrients.get("calories"),
                protein=existing_nutrients.get("protein"),
                carbs=existing_nutrients.get("carbs"),
                fat=existing_nutrients.get("fat"),
                fiber=existing_nutrients.get("fiber"),
                sugar=existing_nutrients.get("sugar"),
                sodium=existing_nutrients.get("sodium"),
            )

            # Apply category enrichment
            enriched_nutrients, was_enriched = self._nutrition_service.apply_category_enrichment(
                nutrients=nutrients,
                quantity_g=adj_quantity,
                category=category,
                enrichment_source="heuristic",
            )

            # Convert back to dict
            result_dict = {
                "calories": enriched_nutrients.calories,
                "protein": enriched_nutrients.protein,
                "carbs": enriched_nutrients.carbs,
                "fat": enriched_nutrients.fat,
                "fiber": enriched_nutrients.fiber,
                "sugar": enriched_nutrients.sugar,
                "sodium": enriched_nutrients.sodium,
            }

            if was_clamped:
                result_dict["quantity_g"] = adj_quantity
                result_dict["garnish_clamped"] = True

            return result_dict, category, was_enriched

        except Exception as e:
            logger.error(f"Error in food classification/enrichment: {e}")
            return existing_nutrients, None, False

    def calculate_bmr(self, physical_data: UserPhysicalData) -> float:
        """Calculate BMR using underlying nutrition service."""
        return self._nutrition_service.calculate_bmr(physical_data)

    def calculate_tdee(self, bmr: float, activity_level: ActivityLevel) -> float:
        """Calculate TDEE using underlying nutrition service."""
        return self._nutrition_service.calculate_tdee(bmr, activity_level)

    def calculate_macro_targets(
        self, tdee: float, strategy: Any, physical_data: UserPhysicalData
    ) -> MacroTargets:
        """Calculate macro targets using underlying nutrition service."""
        return self._nutrition_service.calculate_macro_targets(tdee, strategy, physical_data)

    def recompute_calories_from_macros(self, nutrients: NutrientValues) -> Any:
        """Recompute calories from macros using underlying nutrition service."""
        return self._nutrition_service.recompute_calories_from_macros(nutrients)


# Global singleton for easy access
_integration_service: Optional[NutritionIntegrationService] = None


def get_nutrition_integration_service() -> NutritionIntegrationService:
    """Get or create nutrition integration service singleton."""
    global _integration_service
    if _integration_service is None:
        _integration_service = NutritionIntegrationService()
    return _integration_service


__all__ = [
    "NutritionIntegrationService",
    "get_nutrition_integration_service",
]
