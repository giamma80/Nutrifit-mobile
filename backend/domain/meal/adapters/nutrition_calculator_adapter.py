"""Nutrition calculator adapter - bridges domain to nutrition services.

Provides nutritional calculation capabilities through various adapters:
- Legacy integration with existing nutrition systems
- AI-powered estimation for unknown foods
- Stub implementation for testing
"""

from __future__ import annotations

from typing import Any, Optional

from domain.meal.model import NutrientProfile
from domain.meal.port import NutritionCalculatorPort


class StubNutritionCalculatorAdapter(NutritionCalculatorPort):
    """Stub implementation for testing and development.

    Returns predefined nutritional profiles for common food names.
    Used for testing and as fallback when other services are unavailable.
    """

    def __init__(self) -> None:
        # Predefined nutritional database for common foods
        self._food_database = {
            "chicken breast": NutrientProfile(
                calories_per_100g=165.0,
                protein_per_100g=31.0,
                carbs_per_100g=0.0,
                fat_per_100g=3.6,
                fiber_per_100g=0.0,
                sugar_per_100g=0.0,
                sodium_per_100g=74.0,
            ),
            "salmon fillet": NutrientProfile(
                calories_per_100g=208.0,
                protein_per_100g=25.4,
                carbs_per_100g=0.0,
                fat_per_100g=12.4,
                fiber_per_100g=0.0,
                sugar_per_100g=0.0,
                sodium_per_100g=59.0,
            ),
            "beef steak": NutrientProfile(
                calories_per_100g=271.0,
                protein_per_100g=26.1,
                carbs_per_100g=0.0,
                fat_per_100g=17.4,
                fiber_per_100g=0.0,
                sugar_per_100g=0.0,
                sodium_per_100g=72.0,
            ),
            "basmati rice": NutrientProfile(
                calories_per_100g=356.0,
                protein_per_100g=8.9,
                carbs_per_100g=78.0,
                fat_per_100g=0.6,
                fiber_per_100g=1.8,
                sugar_per_100g=0.0,
                sodium_per_100g=2.0,
            ),
            "greek yogurt": NutrientProfile(
                calories_per_100g=97.0,
                protein_per_100g=9.0,
                carbs_per_100g=3.6,
                fat_per_100g=5.0,
                fiber_per_100g=0.0,
                sugar_per_100g=3.6,
                sodium_per_100g=36.0,
            ),
            "whole wheat bread": NutrientProfile(
                calories_per_100g=247.0,
                protein_per_100g=13.0,
                carbs_per_100g=41.0,
                fat_per_100g=4.2,
                fiber_per_100g=7.0,
                sugar_per_100g=4.0,
                sodium_per_100g=491.0,
            ),
            "banana": NutrientProfile(
                calories_per_100g=89.0,
                protein_per_100g=1.1,
                carbs_per_100g=22.8,
                fat_per_100g=0.3,
                fiber_per_100g=2.6,
                sugar_per_100g=12.2,
                sodium_per_100g=1.0,
            ),
            "apple": NutrientProfile(
                calories_per_100g=52.0,
                protein_per_100g=0.3,
                carbs_per_100g=13.8,
                fat_per_100g=0.2,
                fiber_per_100g=2.4,
                sugar_per_100g=10.4,
                sodium_per_100g=1.0,
            ),
        }

    async def calculate_nutrients(
        self,
        meal_name: str,
        quantity_g: float,
        barcode: Optional[str] = None,
    ) -> Optional[NutrientProfile]:
        """Calculate nutritional profile for meal."""
        # Normalize meal name for lookup
        normalized_name = meal_name.lower().strip()

        # Direct lookup
        profile = self._food_database.get(normalized_name)
        if profile:
            return profile

        # Try partial matching for more flexible lookup
        for food_name, food_profile in self._food_database.items():
            if food_name in normalized_name or normalized_name in food_name:
                return food_profile

        # No match found
        return None

    async def enrich_from_ai(
        self,
        meal_name: str,
        quantity_g: float,
    ) -> Optional[NutrientProfile]:
        """AI-powered nutritional estimation (stub implementation)."""
        # For now, just delegate to the database lookup
        return await self.calculate_nutrients(meal_name, quantity_g)


class LegacyNutritionAdapter(NutritionCalculatorPort):
    """Adapter that bridges to existing nutrition calculation systems.

    Integrates with legacy nutrition services and existing AI meal analysis.
    """

    def __init__(self) -> None:
        self._nutrition_integration: Optional[Any] = None
        self._meal_analysis_service: Optional[Any] = None

        # Lazy initialization to avoid circular imports
        self._init_services()

    def _init_services(self) -> None:
        """Initialize connections to legacy systems."""
        try:
            from domain.nutrition.integration import get_nutrition_integration_service

            self._nutrition_integration = get_nutrition_integration_service()
        except ImportError:
            self._nutrition_integration = None

        try:
            from domain.meal.application.meal_analysis_service import MealAnalysisService

            self._meal_analysis_service = MealAnalysisService.create_with_defaults()
        except ImportError:
            self._meal_analysis_service = None

    async def calculate_nutrients(
        self,
        meal_name: str,
        quantity_g: float,
        barcode: Optional[str] = None,
    ) -> Optional[NutrientProfile]:
        """Calculate nutrients using legacy systems."""
        # Try nutrition domain integration first
        if self._nutrition_integration and self._nutrition_integration._feature_enabled:
            try:
                # Start with empty base nutrients (legacy system enriches them)
                base_nutrients = {
                    "calories": None,
                    "protein": None,
                    "carbs": None,
                    "fat": None,
                    "fiber": None,
                    "sugar": None,
                    "sodium": None,
                }

                # Use enhanced food classification and enrichment
                enriched_nutrients, category, was_enriched = (
                    self._nutrition_integration.classify_and_enrich_food(
                        food_label=meal_name,
                        quantity_g=quantity_g,
                        existing_nutrients=base_nutrients,
                    )
                )

                if enriched_nutrients and was_enriched:
                    # Convert from per-quantity to per-100g
                    scale_factor = 100.0 / quantity_g if quantity_g > 0 else 1.0

                    cal = enriched_nutrients.get("calories", 0.0) or 0.0
                    prot = enriched_nutrients.get("protein", 0.0) or 0.0
                    carbs = enriched_nutrients.get("carbs", 0.0) or 0.0
                    fat = enriched_nutrients.get("fat", 0.0) or 0.0
                    fiber = enriched_nutrients.get("fiber", 0.0) or 0.0
                    sugar = enriched_nutrients.get("sugar", 0.0) or 0.0
                    sodium = enriched_nutrients.get("sodium", 0.0) or 0.0

                    return NutrientProfile(
                        calories_per_100g=cal * scale_factor,
                        protein_per_100g=prot * scale_factor,
                        carbs_per_100g=carbs * scale_factor,
                        fat_per_100g=fat * scale_factor,
                        fiber_per_100g=fiber * scale_factor,
                        sugar_per_100g=sugar * scale_factor,
                        sodium_per_100g=sodium * scale_factor,
                    )
            except Exception:
                pass  # Fallback to other methods

        # Fallback: return None to indicate no calculation available
        return None

    async def enrich_from_ai(
        self,
        meal_name: str,
        quantity_g: float,
    ) -> Optional[NutrientProfile]:
        """Use existing AI systems for nutrition estimation."""
        if not self._meal_analysis_service:
            return None

        try:
            # Create a minimal analysis request
            from domain.meal.model import MealAnalysisRequest
            import datetime

            request = MealAnalysisRequest(
                user_id="meal-enrichment-user",
                photo_id=None,
                photo_url=None,
                now_iso=datetime.datetime.utcnow().isoformat() + "Z",
                normalization_mode="off",
            )

            # Use the existing meal analysis service
            result = await self._meal_analysis_service.analyze_meal_photo(request)

            # Extract nutrition from first item if available
            if result.items:
                item = result.items[0]
                return NutrientProfile(
                    calories_per_100g=item.calories or 0.0,
                    protein_per_100g=item.protein or 0.0,
                    carbs_per_100g=item.carbs or 0.0,
                    fat_per_100g=item.fat or 0.0,
                    fiber_per_100g=item.fiber or 0.0,
                    sugar_per_100g=item.sugar or 0.0,
                    sodium_per_100g=item.sodium or 0.0,
                )

        except Exception:
            pass  # Graceful fallback

        return None


class CompositeNutritionCalculatorAdapter(NutritionCalculatorPort):
    """Composite adapter that tries multiple nutrition sources in order.

    Provides resilient nutrition calculation by trying multiple adapters
    in priority order with graceful fallbacks.
    """

    def __init__(
        self,
        primary: NutritionCalculatorPort,
        fallback: NutritionCalculatorPort,
    ) -> None:
        self._primary = primary
        self._fallback = fallback

    async def calculate_nutrients(
        self,
        meal_name: str,
        quantity_g: float,
        barcode: Optional[str] = None,
    ) -> Optional[NutrientProfile]:
        """Try primary adapter first, then fallback."""
        try:
            result = await self._primary.calculate_nutrients(meal_name, quantity_g, barcode)
            if result:
                return result
        except Exception:
            # Log error but continue to fallback
            pass

        # Try fallback adapter
        try:
            return await self._fallback.calculate_nutrients(meal_name, quantity_g, barcode)
        except Exception:
            # Both adapters failed
            return None

    async def enrich_from_ai(
        self,
        meal_name: str,
        quantity_g: float,
    ) -> Optional[NutrientProfile]:
        """Try AI enrichment with fallback."""
        try:
            result = await self._primary.enrich_from_ai(meal_name, quantity_g)
            if result:
                return result
        except Exception:
            pass

        try:
            return await self._fallback.enrich_from_ai(meal_name, quantity_g)
        except Exception:
            return None
