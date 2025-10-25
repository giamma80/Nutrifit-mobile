"""Stub vision provider for testing.

Returns fake food recognition results without calling external APIs.
Useful for integration/E2E tests.
"""

from typing import Optional

from domain.meal.recognition.entities.recognized_food import FoodRecognitionResult, RecognizedFood


class StubVisionProvider:
    """
    Stub implementation of IVisionProvider for testing.

    Returns hardcoded food recognition results based on hints in the photo URL or description.
    """

    async def analyze_photo(self, photo_url: str, hint: Optional[str] = None) -> FoodRecognitionResult:
        """
        Analyze photo and return stub food items.

        Args:
            photo_url: URL of photo (used to determine stub response)
            hint: Optional hint about the dish

        Returns:
            FoodRecognitionResult with stub items
        """
        # Return different items based on URL pattern
        if "chicken" in photo_url.lower():
            items = [
                RecognizedFood(
                    label="chicken_breast",
                    display_name="Grilled Chicken Breast",
                    quantity_g=150.0,
                    confidence=0.95,
                    category="protein",
                )
            ]
        elif "pasta" in photo_url.lower():
            items = [
                RecognizedFood(
                    label="pasta",
                    display_name="Pasta with Tomato Sauce",
                    quantity_g=200.0,
                    confidence=0.90,
                    category="grains",
                )
            ]
        elif "salad" in photo_url.lower():
            items = [
                RecognizedFood(
                    label="mixed_salad",
                    display_name="Mixed Green Salad",
                    quantity_g=100.0,
                    confidence=0.85,
                    category="vegetables",
                )
            ]
        else:
            # Default response
            items = [
                RecognizedFood(
                    label="mixed_dish",
                    display_name="Mixed Dish",
                    quantity_g=200.0,
                    confidence=0.80,
                    category=None,
                )
            ]

        return FoodRecognitionResult(items=items)

    async def analyze_text(self, description: str) -> FoodRecognitionResult:
        """
        Extract food items from text description.

        Args:
            description: Text description of meal

        Returns:
            FoodRecognitionResult with stub items
        """
        # Simple stub: return single item based on description
        items = [
            RecognizedFood(
                label="text_meal",
                display_name=description[:50],  # Truncate for display
                quantity_g=150.0,
                confidence=0.75,
                category=None,
            )
        ]
        return FoodRecognitionResult(items=items)
