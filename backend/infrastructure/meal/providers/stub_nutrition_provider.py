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
        # Based on production data (USDA + category profiles)
        nutrient_map = {
            # Proteins
            "chicken_breast": {
                "calories": 165.0,
                "protein": 31.0,
                "carbs": 0.0,
                "fat": 3.6,
                "fiber": 0.0,
                "sugar": 0.0,
                "sodium": 74.0,
            },
            "roasted_chicken": {  # Alias for chicken_breast
                "calories": 165.0,
                "protein": 31.0,
                "carbs": 0.0,
                "fat": 3.6,
                "fiber": 0.0,
                "sugar": 0.0,
                "sodium": 74.0,
            },
            "beef": {  # Manzo (like production brasato)
                "calories": 250.0,
                "protein": 26.0,
                "carbs": 0.0,
                "fat": 15.0,
                "fiber": 0.0,
                "sugar": 0.0,
                "sodium": 72.0,
            },
            "chickpeas": {  # Ceci (like production falafel)
                "calories": 388.0,
                "protein": 20.47,
                "carbs": 62.95,
                "fat": 6.04,
                "fiber": 12.2,
                "sugar": 0.0,
                "sodium": 24.0,
            },
            # Vegetables
            "onions": {  # Cipolle
                "calories": 42.0,
                "protein": 0.92,
                "carbs": 9.54,
                "fat": 0.08,
                "fiber": 1.3,
                "sugar": 4.24,
                "sodium": 3.0,
            },
            "parsley": {  # Prezzemolo
                "calories": 36.0,
                "protein": 2.97,
                "carbs": 6.33,
                "fat": 0.79,
                "fiber": 3.3,
                "sugar": 0.85,
                "sodium": 56.0,
            },
            "tomatoes": {  # Pomodori
                "calories": 18.0,
                "protein": 0.88,
                "carbs": 3.89,
                "fat": 0.2,
                "fiber": 1.2,
                "sugar": 2.63,
                "sodium": 5.0,
            },
            "lettuce": {  # Lattuga
                "calories": 15.0,
                "protein": 1.36,
                "carbs": 2.87,
                "fat": 0.15,
                "fiber": 1.3,
                "sugar": 0.78,
                "sodium": 28.0,
            },
            "vegetables": {  # Verdure miste
                "calories": 25.0,
                "protein": 1.5,
                "carbs": 5.0,
                "fat": 0.2,
                "fiber": 2.5,
                "sugar": 2.0,
                "sodium": 15.0,
            },
            # Grains/Carbs
            "pasta": {
                "calories": 140.0,
                "protein": 5.0,
                "carbs": 27.5,
                "fat": 1.0,
                "fiber": 1.5,
                "sugar": 2.5,
                "sodium": 100.0,
            },
            "polenta": {
                "calories": 70.0,
                "protein": 1.6,
                "carbs": 15.0,
                "fat": 0.4,
                "fiber": 1.1,
                "sugar": 0.3,
                "sodium": 1.0,
            },
            "potatoes": {  # Patate
                "calories": 77.0,
                "protein": 2.05,
                "carbs": 17.49,
                "fat": 0.09,
                "fiber": 2.1,
                "sugar": 0.82,
                "sodium": 6.0,
            },
            # Condiments/Oils
            "sauce": {  # Salsa
                "calories": 438.0,
                "protein": 1.6,
                "carbs": 10.8,
                "fat": 42.6,
                "fiber": 1.3,
                "sugar": 6.2,
                "sodium": 643.0,
            },
            "tomato_sauce": {  # Sugo al pomodoro
                "calories": 29.0,
                "protein": 1.26,
                "carbs": 6.17,
                "fat": 0.15,
                "fiber": 1.5,
                "sugar": 3.91,
                "sodium": 297.0,
            },
            "olive_oil": {  # Olio d'oliva
                "calories": 884.0,
                "protein": 0.0,
                "carbs": 0.0,
                "fat": 100.0,
                "fiber": 0.0,
                "sugar": 0.0,
                "sodium": 2.0,
            },
            "sesame": {  # Sesamo
                "calories": 565.0,
                "protein": 11.63,
                "carbs": 50.26,
                "fat": 33.28,
                "fiber": 7.72,
                "sugar": 0.0,
                "sodium": 166.8,
            },
            "spices": {  # Spezie
                "calories": 415.0,
                "protein": 5.76,
                "carbs": 69.28,
                "fat": 12.66,
                "fiber": 14.85,
                "sugar": 0.0,
                "sodium": 52.0,
            },
            "parmesan": {  # Parmigiano
                "calories": 431.0,
                "protein": 38.46,
                "carbs": 3.22,
                "fat": 28.61,
                "fiber": 0.0,
                "sugar": 0.9,
                "sodium": 1529.0,
            },
            # Generics
            "protein": {  # Generic protein
                "calories": 165.0,
                "protein": 30.0,
                "carbs": 0.0,
                "fat": 4.0,
                "fiber": 0.0,
                "sugar": 0.0,
                "sodium": 70.0,
            },
            "carbs": {  # Generic carbs
                "calories": 130.0,
                "protein": 4.0,
                "carbs": 25.0,
                "fat": 1.0,
                "fiber": 2.0,
                "sugar": 1.0,
                "sodium": 5.0,
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
