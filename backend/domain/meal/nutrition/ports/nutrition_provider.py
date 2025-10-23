"""Port (interface) for nutrition data providers.

This port defines the contract that external nutrition data providers
(e.g., USDA client) must implement to be used by the domain layer.
"""

from typing import Optional, Protocol

from domain.meal.nutrition.entities.nutrient_profile import NutrientProfile


class INutritionProvider(Protocol):
    """
    Interface for nutrition data providers.

    This port follows the Dependency Inversion Principle:
    - Domain layer defines the interface (port)
    - Infrastructure layer implements it (adapter)

    Implementations can be:
    - USDA API client (high quality)
    - Category-based provider (medium quality)
    - Fallback provider (low quality, generic estimates)
    """

    async def get_nutrients(
        self, identifier: str, quantity_g: float
    ) -> Optional[NutrientProfile]:
        """
        Get nutrient profile for a food identifier.

        Args:
            identifier: Food identifier. Can be:
                - Food label/name (e.g., "chicken breast", "banana")
                - Category name (e.g., "vegetables", "grains")
                - FDC ID for USDA (e.g., "173096")
            quantity_g: Reference quantity in grams (typically 100.0)

        Returns:
            NutrientProfile if found, None if not available

        Raises:
            Exception: Implementation-specific errors (network, API, etc.)

        Example:
            >>> provider = USDANutritionProvider()
            >>> profile = await provider.get_nutrients("chicken breast", 100.0)
            >>> if profile:
            ...     print(f"Calories: {profile.calories}")
        """
        ...
