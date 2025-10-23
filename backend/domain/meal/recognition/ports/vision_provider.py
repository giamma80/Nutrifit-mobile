"""Port (interface) for vision AI providers.

This port defines the contract that external vision AI providers
(e.g., OpenAI GPT-4 Vision) must implement to be used by the domain layer.
"""

from typing import Optional, Protocol

from domain.meal.recognition.entities.recognized_food import FoodRecognitionResult


class IVisionProvider(Protocol):
    """
    Interface for vision AI providers.

    This port follows the Dependency Inversion Principle:
    - Domain layer defines the interface (port)
    - Infrastructure layer implements it (adapter)

    Implementations can be:
    - OpenAI GPT-4 Vision (high quality)
    - Google Cloud Vision (alternative)
    - Mock provider (for testing)
    """

    async def analyze_photo(
        self, photo_url: str, hint: Optional[str] = None
    ) -> FoodRecognitionResult:
        """
        Analyze photo and recognize food items.

        Args:
            photo_url: URL of the food photo to analyze
            hint: Optional hint from user about the dish (e.g., "pizza", "salad")
                  Helps improve recognition accuracy

        Returns:
            FoodRecognitionResult with recognized items

        Raises:
            Exception: Implementation-specific errors (network, API, parsing, etc.)

        Example:
            >>> provider = OpenAIVisionProvider()
            >>> result = await provider.analyze_photo(
            ...     "https://example.com/food.jpg",
            ...     hint="pasta dish"
            ... )
            >>> for item in result.items:
            ...     print(f"{item.display_name}: {item.quantity_g}g")
        """
        ...

    async def analyze_text(self, description: str) -> FoodRecognitionResult:
        """
        Extract food items from text description.

        Useful for manual text entry where user describes what they ate.

        Args:
            description: Text description of the meal
                        (e.g., "I had spaghetti with tomato sauce and a chicken breast")

        Returns:
            FoodRecognitionResult with extracted items

        Raises:
            Exception: Implementation-specific errors (network, API, parsing, etc.)

        Example:
            >>> provider = OpenAIVisionProvider()
            >>> result = await provider.analyze_text(
            ...     "I ate 150g of grilled chicken and 200g of rice"
            ... )
            >>> result.item_count()
            2
        """
        ...
