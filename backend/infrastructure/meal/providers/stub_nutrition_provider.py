"""Stub nutrition provider for testing.

Returns fake nutrient profiles without calling external APIs (USDA, etc.).
Useful for integration/E2E tests.
"""

from typing import Optional

from domain.meal.nutrition.entities.nutrient_profile import NutrientProfile


class StubNutritionProvider:
    """
    Stub implementation of INutritionProvider for testing.

    Returns hardcoded nutrient profiles based on food label.
    """

    async def enrich(self, label: str, quantity_g: float, category: Optional[str] = None) -> Optional[NutrientProfile]:
        """
        Enrich food label with nutrient data (stub implementation).

        This method provides compatibility with NutritionEnrichmentService interface.
        Simply delegates to get_nutrients().

        Args:
            label: Food label/name
            quantity_g: Quantity in grams
            category: Optional category (ignored in stub)

        Returns:
            NutrientProfile with stub data (scaled to quantity_g)
        """
        return await self.get_nutrients(label, quantity_g)

    async def get_nutrients(self, identifier: str, quantity_g: float) -> Optional[NutrientProfile]:
        """
        Get stub nutrient profile for a food identifier.

        Args:
            identifier: Food label/name
            quantity_g: Reference quantity in grams

        Returns:
            NutrientProfile with stub data (scaled to quantity_g)
        """
        # Map common foods to nutrient profiles (per 100g)
        nutrient_map = {
            "chicken_breast": {
                "calories": 165.0,
                "protein": 31.0,
                "carbs": 0.0,
                "fat": 3.6,
                "fiber": 0.0,
                "sugar": 0.0,
                "sodium": 74.0,
            },
            "roasted_chicken": {
                "calories": 165.0,
                "protein": 31.0,
                "carbs": 0.0,
                "fat": 3.6,
                "fiber": 0.0,
                "sugar": 0.0,
                "sodium": 74.0,
            },
            "pasta": {
                "calories": 140.0,
                "protein": 5.0,
                "carbs": 27.5,
                "fat": 1.0,
                "fiber": 1.5,
                "sugar": 2.5,
                "sodium": 100.0,
            },
            "mixed_salad": {
                "calories": 20.0,
                "protein": 1.5,
                "carbs": 4.0,
                "fat": 0.2,
                "fiber": 2.0,
                "sugar": 1.5,
                "sodium": 10.0,
            },
            "nutella": {
                "calories": 539.0,
                "protein": 6.3,
                "carbs": 57.5,
                "fat": 30.9,
                "fiber": 0.0,
                "sugar": 56.3,
                "sodium": 40.0,
            },
        }

        # Get base nutrients (per 100g) or use defaults
        base_nutrients = nutrient_map.get(
            identifier,
            {
                "calories": 150.0,
                "protein": 10.0,
                "carbs": 20.0,
                "fat": 5.0,
                "fiber": 2.0,
                "sugar": 3.0,
                "sodium": 50.0,
            },
        )

        # Scale to requested quantity
        scale_factor = quantity_g / 100.0

        return NutrientProfile(
            calories=int(base_nutrients["calories"] * scale_factor),
            protein=base_nutrients["protein"] * scale_factor,
            carbs=base_nutrients["carbs"] * scale_factor,
            fat=base_nutrients["fat"] * scale_factor,
            fiber=base_nutrients["fiber"] * scale_factor if base_nutrients["fiber"] else 0.0,
            sugar=base_nutrients["sugar"] * scale_factor if base_nutrients["sugar"] else 0.0,
            sodium=base_nutrients["sodium"] * scale_factor if base_nutrients["sodium"] else 0.0,
            quantity_g=quantity_g,
        )
