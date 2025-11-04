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
    Supports async context manager protocol for lifespan compatibility.
    """

    async def __aenter__(self) -> "StubVisionProvider":
        """Enter async context (no-op for stub)."""
        return self

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Exit async context (no-op for stub)."""
        return None

    async def analyze_photo(
        self, photo_url: str, hint: Optional[str] = None
    ) -> FoodRecognitionResult:
        """
        Analyze photo and return stub food items.

        Simulates production behavior with:
        - Multiple ingredients per dish (3-5 items)
        - Italian display names
        - Realistic quantities
        - confidence = 1.0 (matching production)

        Args:
            photo_url: URL of photo (used to determine stub response)
            hint: Optional hint about the dish

        Returns:
            FoodRecognitionResult with stub items (matching production structure)
        """
        # Return different items based on URL pattern
        if "brasato" in photo_url.lower() or "beef" in photo_url.lower():
            # Brasato al Barolo (like production)
            items = [
                RecognizedFood(
                    label="beef",
                    display_name="manzo",
                    quantity_g=200.0,
                    confidence=1.0,
                    category="protein",
                ),
                RecognizedFood(
                    label="sauce",
                    display_name="salsa",
                    quantity_g=100.0,
                    confidence=1.0,
                    category=None,
                ),
                RecognizedFood(
                    label="polenta",
                    display_name="polenta",
                    quantity_g=150.0,
                    confidence=1.0,
                    category="grains",
                ),
            ]
        elif "falafel" in photo_url.lower():
            # Falafel (like production)
            items = [
                RecognizedFood(
                    label="chickpeas",
                    display_name="ceci",
                    quantity_g=100.0,
                    confidence=1.0,
                    category="protein",
                ),
                RecognizedFood(
                    label="onions",
                    display_name="cipolle",
                    quantity_g=50.0,
                    confidence=1.0,
                    category="vegetables",
                ),
                RecognizedFood(
                    label="parsley",
                    display_name="prezzemolo",
                    quantity_g=10.0,
                    confidence=1.0,
                    category="vegetables",
                ),
                RecognizedFood(
                    label="sesame",
                    display_name="sesamo",
                    quantity_g=10.0,
                    confidence=1.0,
                    category=None,
                ),
                RecognizedFood(
                    label="spices",
                    display_name="spezie",
                    quantity_g=5.0,
                    confidence=1.0,
                    category=None,
                ),
            ]
        elif "chicken" in photo_url.lower() or "pollo" in photo_url.lower():
            # Chicken dish
            items = [
                RecognizedFood(
                    label="chicken_breast",
                    display_name="petto di pollo",
                    quantity_g=150.0,
                    confidence=1.0,
                    category="protein",
                ),
                RecognizedFood(
                    label="vegetables",
                    display_name="verdure miste",
                    quantity_g=100.0,
                    confidence=1.0,
                    category="vegetables",
                ),
                RecognizedFood(
                    label="potatoes",
                    display_name="patate",
                    quantity_g=120.0,
                    confidence=1.0,
                    category="grains",
                ),
            ]
        elif "pasta" in photo_url.lower():
            # Pasta dish
            items = [
                RecognizedFood(
                    label="pasta",
                    display_name="pasta",
                    quantity_g=200.0,
                    confidence=1.0,
                    category="grains",
                ),
                RecognizedFood(
                    label="tomato_sauce",
                    display_name="sugo al pomodoro",
                    quantity_g=80.0,
                    confidence=1.0,
                    category="vegetables",
                ),
                RecognizedFood(
                    label="parmesan",
                    display_name="parmigiano",
                    quantity_g=20.0,
                    confidence=1.0,
                    category="protein",
                ),
            ]
        elif "salad" in photo_url.lower() or "insalata" in photo_url.lower():
            # Salad
            items = [
                RecognizedFood(
                    label="lettuce",
                    display_name="lattuga",
                    quantity_g=80.0,
                    confidence=1.0,
                    category="vegetables",
                ),
                RecognizedFood(
                    label="tomatoes",
                    display_name="pomodori",
                    quantity_g=60.0,
                    confidence=1.0,
                    category="vegetables",
                ),
                RecognizedFood(
                    label="olive_oil",
                    display_name="olio d'oliva",
                    quantity_g=10.0,
                    confidence=1.0,
                    category=None,
                ),
            ]
        else:
            # Default: Generic mixed dish (3 real ingredients)
            items = [
                RecognizedFood(
                    label="chicken_breast",
                    display_name="petto di pollo",
                    quantity_g=120.0,
                    confidence=1.0,
                    category="protein",
                ),
                RecognizedFood(
                    label="rice",
                    display_name="riso",
                    quantity_g=150.0,
                    confidence=1.0,
                    category="grains",
                ),
                RecognizedFood(
                    label="vegetables",
                    display_name="verdure miste",
                    quantity_g=80.0,
                    confidence=1.0,
                    category="vegetables",
                ),
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
