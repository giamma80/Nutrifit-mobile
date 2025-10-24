"""Enrich nutrients query - utility to test nutrition enrichment capability."""

from dataclasses import dataclass
import logging

from domain.meal.nutrition.entities.nutrient_profile import NutrientProfile
from domain.meal.nutrition.services.enrichment_service import (
    NutritionEnrichmentService,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EnrichNutrientsQuery:
    """
    Utility Query: Enrich food with nutrition data.

    Atomic query to test nutrition enrichment without creating meals.
    Useful for:
    - Testing USDA API integration
    - Debug/troubleshooting
    - Preview nutrition data

    Attributes:
        food_label: Food label to enrich (e.g., "roasted_chicken", "apple")
        quantity_g: Quantity in grams
    """
    food_label: str
    quantity_g: float


class EnrichNutrientsQueryHandler:
    """Handler for EnrichNutrientsQuery."""

    def __init__(self, enrichment_service: NutritionEnrichmentService):
        """
        Initialize handler.

        Args:
            enrichment_service: Nutrition enrichment service
        """
        self._enrichment = enrichment_service

    async def handle(self, query: EnrichNutrientsQuery) -> NutrientProfile:
        """
        Execute enrichment query.

        Args:
            query: EnrichNutrientsQuery

        Returns:
            NutrientProfile with nutrition data

        Raises:
            ValueError: If enrichment fails or food not found

        Example:
            >>> handler = EnrichNutrientsQueryHandler(enrichment_service)
            >>> query = EnrichNutrientsQuery(
            ...     food_label="roasted_chicken",
            ...     quantity_g=150.0
            ... )
            >>> profile = await handler.handle(query)
            >>> profile.calories > 0
            True
        """
        logger.info(
            "Enriching food with nutrition data",
            extra={
                "food_label": query.food_label,
                "quantity_g": query.quantity_g,
            },
        )

        # Get nutrient profile (uses cascade: USDA → Category → Fallback)
        profile = await self._enrichment.enrich(
            label=query.food_label,
            quantity_g=query.quantity_g
        )

        logger.info(
            "Nutrition enrichment completed",
            extra={
                "food_label": query.food_label,
                "quantity_g": query.quantity_g,
                "calories": profile.calories,
                "protein_g": profile.protein,
                "is_high_quality": profile.is_high_quality(),
            },
        )

        return profile
