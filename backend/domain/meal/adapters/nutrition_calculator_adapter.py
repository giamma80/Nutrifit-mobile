"""Nutrition calculator adapter - bridges domain to nutrition services.

Provides nutritional calculation capabilities through various adapters:
- Legacy integration with existing nutrition systems
- AI-powered estimation for unknown foods
- Stub implementation for testing
"""

from __future__ import annotations

from typing import Optional

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
        # TODO: Initialize connections to legacy systems
        pass

    async def calculate_nutrients(
        self,
        meal_name: str,
        quantity_g: float,
        barcode: Optional[str] = None,
    ) -> Optional[NutrientProfile]:
        """Calculate nutrients using legacy systems."""
        # TODO: Integrate with existing nutrition calculation logic
        # - Bridge to rules/category_profiles.py if needed
        # - Use existing AI meal analysis results
        # - Apply portion scaling and normalization
        raise NotImplementedError(
            "Legacy nutrition integration not implemented"
        )

    async def enrich_from_ai(
        self,
        meal_name: str,
        quantity_g: float,
    ) -> Optional[NutrientProfile]:
        """Use existing AI systems for nutrition estimation."""
        # TODO: Integration with existing AI meal photo analysis
        # - Bridge to domain.meal.application.meal_analysis_service
        # - Use GPT-4V or other AI models for estimation
        # - Handle confidence scoring and fallbacks
        raise NotImplementedError("AI nutrition integration not implemented")


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
            result = await self._primary.calculate_nutrients(
                meal_name, quantity_g, barcode
            )
            if result:
                return result
        except Exception:
            # Log error but continue to fallback
            pass

        # Try fallback adapter
        try:
            return await self._fallback.calculate_nutrients(
                meal_name, quantity_g, barcode
            )
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
