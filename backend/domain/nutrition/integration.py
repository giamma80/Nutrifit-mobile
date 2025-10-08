"""Integration service for nutrition domain with existing GraphQL layer.

Provides backward-compatible interface while enabling gradual rollout
of new nutrition domain through feature flag AI_NUTRITION_V2.
"""

from __future__ import annotations

import logging
import os
from typing import Optional, Dict, Any

from domain.nutrition.application.nutrition_service import (
    NutritionCalculationService,
    get_nutrition_service,
)
from domain.nutrition.model import DailyNutritionSummary as DomainSummary


logger = logging.getLogger("domain.nutrition.integration")


class NutritionIntegrationService:
    """Integration layer tra nutrition domain e GraphQL esistente."""
    
    def __init__(self):
        self._nutrition_service: Optional[NutritionCalculationService] = None
        self._feature_enabled = self._check_feature_flag()
        
        if self._feature_enabled:
            try:
                self._nutrition_service = get_nutrition_service()
                logger.info("Nutrition domain V2 enabled and initialized")
            except Exception as e:
                logger.error(f"Failed to initialize nutrition V2: {e}")
                self._feature_enabled = False
    
    def _check_feature_flag(self) -> bool:
        """Check AI_NUTRITION_V2 feature flag."""
        return os.getenv("AI_NUTRITION_V2", "false").lower() == "true"
    
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
        if not self._feature_enabled or not self._nutrition_service:
            return fallback_summary
        
        try:
            # Calculate enhanced summary using nutrition domain
            domain_summary = self._nutrition_service.calculate_daily_summary(
                user_id=user_id,
                date=date,
            )
            
            # Merge with existing summary, keeping backward compatibility
            enhanced = fallback_summary.copy()
            
            # Add new fields from nutrition domain
            enhanced.update({
                "nutrition_v2_enabled": True,
                "target_adherence": domain_summary.target_adherence,
                "macro_balance_score": domain_summary.macro_balance_score,
                "enhanced_calculations": {
                    "deficit_v2": domain_summary.calories_deficit,
                    "replenished_pct_v2": domain_summary.calories_replenished_percent,
                },
            })
            
            logger.debug(f"Enhanced daily summary for {user_id}/{date}")
            return enhanced
            
        except Exception as e:
            logger.error(f"Error in enhanced daily summary: {e}")
            # Graceful fallback to existing logic
            return fallback_summary
    
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
        if not self._feature_enabled or not self._nutrition_service:
            # Fallback to legacy logic
            return self._legacy_recompute_calories(
                protein, carbs, fat, existing_calories
            )
        
        try:
            from domain.nutrition.model import NutrientValues
            
            nutrients = NutrientValues(
                protein=protein,
                carbs=carbs,
                fat=fat,
                calories=existing_calories,
            )
            
            return self._nutrition_service.recompute_calories_from_macros(nutrients)
            
        except Exception as e:
            logger.error(f"Error in nutrition V2 calorie recompute: {e}")
            # Graceful fallback
            return self._legacy_recompute_calories(
                protein, carbs, fat, existing_calories
            )
    
    def _legacy_recompute_calories(
        self,
        protein: Optional[float],
        carbs: Optional[float],
        fat: Optional[float],
        existing_calories: Optional[float],
    ) -> tuple[Optional[float], bool]:
        """Legacy calorie recomputation from rules/category_profiles.py."""
        if protein is None and carbs is None and fat is None:
            return existing_calories, False
            
        p = protein or 0.0
        c = carbs or 0.0
        f = fat or 0.0
        calculated = p * 4 + c * 4 + f * 9
        
        if existing_calories is None:
            return round(calculated, 1), True
            
        # Consistency check
        delta = abs(calculated - existing_calories)
        if existing_calories > 0 and (delta / existing_calories) > 0.15:
            return round(calculated, 1), True
            
        return existing_calories, False
    
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
        if not self._feature_enabled or not self._nutrition_service:
            return existing_nutrients, None, False
        
        try:
            # Classify food using category adapter
            category_adapter = self._nutrition_service.category_profile_port
            category = category_adapter.classify_food(food_label)
            
            if not category:
                return existing_nutrients, None, False
            
            # Apply garnish clamp if needed
            adj_quantity, was_clamped = category_adapter.apply_garnish_clamp(
                quantity_g, category
            )
            
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
            enriched_nutrients, was_enriched = (
                self._nutrition_service.apply_category_enrichment(
                    nutrients=nutrients,
                    quantity_g=adj_quantity,
                    category=category,
                    enrichment_source="heuristic",
                )
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