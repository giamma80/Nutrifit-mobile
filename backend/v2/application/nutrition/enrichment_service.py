"""
Nutrition Enrichment Service.

Orchestrates USDA API calls, caching, and fallback logic.
"""

from typing import Optional

import structlog

from backend.v2.domain.meal.nutrition.models import (
    NutrientProfile,
    NutrientSource,
)
from backend.v2.domain.meal.nutrition.usda_mapper import USDAMapper
from backend.v2.domain.shared.value_objects import Barcode
from backend.v2.infrastructure.usda.api_client import USDAApiClient
from backend.v2.infrastructure.usda.cache import USDACache
from backend.v2.infrastructure.usda.category_profiles import (
    infer_category,
    get_category_profile,
)

logger = structlog.get_logger(__name__)


class NutritionEnrichmentService:
    """Orchestrates nutrition data enrichment.

    Flow:
    1. Check cache
    2. Query USDA API
    3. Fallback to category profiles
    """

    def __init__(self, api_client: USDAApiClient, cache: Optional[USDACache] = None) -> None:
        """Initialize service.

        Args:
            api_client: USDA API client
            cache: Optional cache instance
        """
        self.api_client = api_client
        self.cache = cache or USDACache()

    async def enrich_by_barcode(self, barcode: Barcode) -> Optional[NutrientProfile]:
        """Enrich nutrients by barcode.

        Args:
            barcode: Product barcode

        Returns:
            Nutrient profile or None if not found

        Example:
            >>> async def test():
            ...     async with USDAApiClient(api_key="test") as client:
            ...         service = NutritionEnrichmentService(client)
            ...         barcode = Barcode(value="3017620422003")
            ...         profile = await service.enrich_by_barcode(barcode)
            ...         return profile
        """
        # Check cache first
        cached_item = self.cache.get_by_barcode(barcode)
        if cached_item:
            logger.info("Using cached barcode data", barcode=barcode.value)
            return USDAMapper.to_nutrient_profile(cached_item)

        # Query USDA API
        try:
            result = await self.api_client.search_by_barcode(barcode)

            if result and result.foods:
                food_item = result.foods[0]
                self.cache.set_by_barcode(barcode, food_item)

                logger.info(
                    "Enriched from USDA API",
                    barcode=barcode.value,
                    description=food_item.description,
                )

                return USDAMapper.to_nutrient_profile(food_item)

        except Exception as e:
            logger.warning(
                "USDA API lookup failed",
                barcode=barcode.value,
                error=str(e),
            )

        # Not found
        logger.info("Barcode not found in USDA", barcode=barcode.value)
        return None

    async def enrich_by_description(
        self, description: str, quantity_g: float = 100.0
    ) -> NutrientProfile:
        """Enrich nutrients by food description.

        Falls back to category profiles if USDA lookup fails.

        Args:
            description: Food description
            quantity_g: Quantity in grams (for scaling)

        Returns:
            Nutrient profile (never None, uses fallback)

        Example:
            >>> async def test():
            ...     async with USDAApiClient(api_key="test") as client:
            ...         service = NutritionEnrichmentService(client)
            ...         profile = await service.enrich_by_description(
            ...             "Apple, raw"
            ...         )
            ...         assert profile is not None
            ...         return profile
        """
        # Check cache first
        cached_item = self.cache.get_by_description(description)
        if cached_item:
            logger.info("Using cached description data", desc=description)
            profile = USDAMapper.to_nutrient_profile(cached_item)
            return profile.scale_to_quantity(quantity_g)

        # Query USDA API
        try:
            result = await self.api_client.search_by_description(description, max_results=1)

            if result.foods:
                food_item = result.foods[0]
                self.cache.set_by_description(description, food_item)

                logger.info(
                    "Enriched from USDA API",
                    query=description,
                    match=food_item.description,
                )

                profile = USDAMapper.to_nutrient_profile(food_item)
                return profile.scale_to_quantity(quantity_g)

        except Exception as e:
            logger.warning(
                "USDA API lookup failed",
                description=description,
                error=str(e),
            )

        # Fallback to category profile
        category = infer_category(description)
        category_profile = get_category_profile(category)

        logger.info(
            "Using category fallback",
            description=description,
            category=category.value,
        )

        return NutrientProfile(
            calories=category_profile.calories_per_100g,
            protein=category_profile.protein_per_100g,
            carbs=category_profile.carbs_per_100g,
            fat=category_profile.fat_per_100g,
            fiber=category_profile.fiber_per_100g,
            sugar=category_profile.sugar_per_100g,
            sodium=category_profile.sodium_per_100g,
            source=NutrientSource.ESTIMATED,
        ).scale_to_quantity(quantity_g)

    async def enrich_batch(self, descriptions: list[str]) -> list[NutrientProfile]:
        """Enrich multiple food descriptions.

        Args:
            descriptions: List of food descriptions

        Returns:
            List of nutrient profiles

        Example:
            >>> async def test():
            ...     async with USDAApiClient(api_key="test") as client:
            ...         service = NutritionEnrichmentService(client)
            ...         profiles = await service.enrich_batch([
            ...             "Apple",
            ...             "Banana",
            ...             "Orange",
            ...         ])
            ...         assert len(profiles) == 3
            ...         return profiles
        """
        import asyncio

        tasks = [self.enrich_by_description(desc) for desc in descriptions]
        return await asyncio.gather(*tasks)
