"""Domain service for enriching food items with nutritional data.

This service implements a cascade strategy to find the best available
nutritional data for a given food item.
"""

import logging
from typing import Optional

from domain.meal.nutrition.entities.nutrient_profile import NutrientProfile
from domain.meal.nutrition.ports.nutrition_provider import INutritionProvider

logger = logging.getLogger(__name__)


class NutritionEnrichmentService:
    """
    Domain service for enriching food items with nutrients.

    Implements a cascading strategy to maximize data quality:
    1. USDA database (highest quality - verified data)
    2. Category-based profile (medium quality - category averages)
    3. Generic fallback (lowest quality - basic estimates)

    This service orchestrates multiple nutrition providers following
    the ports pattern, allowing different implementations without
    changing domain logic.
    """

    def __init__(
        self,
        usda_provider: INutritionProvider,
        category_provider: INutritionProvider,
        fallback_provider: INutritionProvider,
    ):
        """
        Initialize enrichment service with cascade providers.

        Args:
            usda_provider: Primary provider (USDA API)
            category_provider: Secondary provider (category averages)
            fallback_provider: Tertiary provider (generic estimates)
        """
        self._usda = usda_provider
        self._category = category_provider
        self._fallback = fallback_provider

    async def enrich(
        self,
        label: str,
        quantity_g: float,
        category: Optional[str] = None,
    ) -> NutrientProfile:
        """
        Enrich food label with nutrient data using cascade strategy.

        Tries providers in order of data quality:
        1. USDA (if available)
        2. Category (if category provided and available)
        3. Fallback (always succeeds with generic data)

        Args:
            label: Food label (e.g., "chicken breast", "banana")
            quantity_g: Quantity in grams
            category: Optional category hint (e.g., "vegetables", "meat")

        Returns:
            NutrientProfile scaled to requested quantity

        Raises:
            ValueError: If quantity_g is not positive

        Example:
            >>> service = NutritionEnrichmentService(usda, category, fallback)
            >>> profile = await service.enrich("chicken breast", 150.0, "meat")
            >>> print(f"Calories: {profile.calories}")
            >>> print(f"Source: {profile.source}")  # "USDA" if found
        """
        if quantity_g <= 0:
            raise ValueError(f"Quantity must be positive, got {quantity_g}")

        # Strategy 1: Try USDA first (highest quality)
        try:
            profile = await self._usda.get_nutrients(label, 100.0)
            if profile:
                logger.info(
                    "USDA enrichment success",
                    extra={"label": label, "source": "USDA", "confidence": profile.confidence},
                )
                return profile.scale_to_quantity(quantity_g)
        except Exception as e:
            logger.warning(
                "USDA enrichment failed",
                extra={"label": label, "error": str(e)},
            )

        # Strategy 2: Try category profile (medium quality)
        if category:
            try:
                profile = await self._category.get_nutrients(category, 100.0)
                if profile:
                    logger.info(
                        "Category enrichment success",
                        extra={"label": label, "category": category, "source": "CATEGORY"},
                    )
                    return profile.scale_to_quantity(quantity_g)
            except Exception as e:
                logger.warning(
                    "Category enrichment failed",
                    extra={"category": category, "error": str(e)},
                )

        # Strategy 3: Fallback to generic (always succeeds)
        logger.info(
            "Fallback enrichment",
            extra={"label": label, "reason": "USDA and category unavailable"},
        )
        profile = await self._fallback.get_nutrients("generic", 100.0)

        # Fallback should always return a profile
        if profile is None:
            # This should never happen, but handle gracefully
            logger.error("Fallback provider returned None - creating minimal profile")
            profile = NutrientProfile(
                calories=100,
                protein=5.0,
                carbs=15.0,
                fat=3.0,
                source="AI_ESTIMATE",
                confidence=0.3,
                quantity_g=100.0,
            )

        return profile.scale_to_quantity(quantity_g)

    async def enrich_batch(
        self,
        items: list[tuple[str, float, Optional[str]]],
    ) -> list[NutrientProfile]:
        """
        Enrich multiple food items in batch.

        Useful for enriching all items in a meal at once.

        Args:
            items: List of (label, quantity_g, category) tuples

        Returns:
            List of NutrientProfiles in same order as input

        Example:
            >>> items = [
            ...     ("chicken breast", 150.0, "meat"),
            ...     ("rice", 200.0, "grains"),
            ...     ("broccoli", 100.0, "vegetables"),
            ... ]
            >>> profiles = await service.enrich_batch(items)
            >>> for profile in profiles:
            ...     print(f"{profile.calories} kcal")
        """
        # Process items sequentially for now
        # TODO: Could be optimized with asyncio.gather() for parallel requests
        profiles = []
        for label, quantity_g, category in items:
            profile = await self.enrich(label, quantity_g, category)
            profiles.append(profile)

        return profiles
