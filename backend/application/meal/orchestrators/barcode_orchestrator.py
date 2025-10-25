"""Barcode analysis orchestrator.

Coordinates barcode lookup and nutrition enrichment for barcode-based meal analysis.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4
import logging

from domain.meal.core.entities.meal import Meal
from domain.meal.core.factories.meal_factory import MealFactory
from domain.meal.barcode.services.barcode_service import BarcodeService
from domain.meal.nutrition.services.enrichment_service import NutritionEnrichmentService

logger = logging.getLogger(__name__)


class BarcodeOrchestrator:
    """
    Orchestrate barcode-based meal analysis workflow.

    Coordinates barcode lookup and nutrition enrichment to transform
    a product barcode into a complete Meal aggregate.

    Flow:
    1. Lookup product by barcode (Barcode Service)
    2. Enrich with nutrients if needed (Nutrition Service)
    3. Scale nutrients to actual quantity
    4. Create Meal aggregate (Meal Factory)

    Example:
        >>> orchestrator = BarcodeOrchestrator(
        ...     barcode_service,
        ...     nutrition_service,
        ...     meal_factory
        ... )
        >>> meal = await orchestrator.analyze(
        ...     user_id="user123",
        ...     barcode="8001505005707",
        ...     quantity_g=150.0,
        ...     meal_type="SNACK"
        ... )
    """

    def __init__(
        self,
        barcode_service: BarcodeService,
        nutrition_service: NutritionEnrichmentService,
        meal_factory: MealFactory,
    ):
        """
        Initialize orchestrator.

        Args:
            barcode_service: Service for barcode product lookup
            nutrition_service: Service for nutrition enrichment
            meal_factory: Factory for creating Meal aggregates
        """
        self._barcode = barcode_service
        self._nutrition = nutrition_service
        self._factory = meal_factory

    async def analyze(
        self,
        user_id: str,
        barcode: str,
        quantity_g: float,
        meal_type: str = "SNACK",
        timestamp: Optional[datetime] = None,
    ) -> Meal:
        """
        Orchestrate complete barcode analysis workflow.

        Args:
            user_id: User ID who owns this meal
            barcode: Product barcode (EAN/UPC)
            quantity_g: Actual quantity consumed in grams
            meal_type: BREAKFAST | LUNCH | DINNER | SNACK
            timestamp: Meal timestamp (default: current time)

        Returns:
            Analyzed Meal aggregate with product data

        Raises:
            ValueError: If product not found or barcode invalid
            Exception: If any service fails during orchestration

        Example:
            >>> meal = await orchestrator.analyze(
            ...     user_id="user123",
            ...     barcode="8001505005707",
            ...     quantity_g=150.0,
            ...     meal_type="SNACK"
            ... )
            >>> meal.entries[0].name  # Product name
            'Nutella'
        """
        logger.info(
            "Orchestrating barcode analysis",
            extra={
                "user_id": user_id,
                "barcode": barcode,
                "quantity_g": quantity_g,
                "meal_type": meal_type,
            },
        )

        # 1. Lookup product by barcode
        product = await self._barcode.lookup(barcode)

        if not product:
            raise ValueError(f"Product not found for barcode: {barcode}")

        logger.info(
            "Product found",
            extra={
                "barcode": barcode,
                "product_name": product.name,
                "brand": product.brand,
                "has_nutrients": product.nutrients is not None,
            },
        )

        # 2. Get/enrich nutrients
        if product.nutrients:
            # Product already has nutrients from barcode database
            base_nutrients = product.nutrients
            logger.debug("Using nutrients from barcode database")
        else:
            # Enrich from USDA (fallback)
            logger.info(
                "No nutrients in barcode database, enriching from USDA",
                extra={"product_name": product.name},
            )

            base_nutrients = await self._nutrition.enrich(
                label=product.name,
                quantity_g=100.0,  # Reference quantity
                category=None,  # Product category not available
            )

        # 3. Scale nutrients to actual quantity
        # Base nutrients are typically per 100g
        serving_size = product.serving_size_g or 100.0
        scale_factor = quantity_g / serving_size

        scaled_nutrients_dict = {
            "calories": int(base_nutrients.calories * scale_factor),
            "protein": base_nutrients.protein * scale_factor,
            "carbs": base_nutrients.carbs * scale_factor,
            "fat": base_nutrients.fat * scale_factor,
            "fiber": base_nutrients.fiber * scale_factor if base_nutrients.fiber else 0.0,
            "sugar": base_nutrients.sugar * scale_factor if base_nutrients.sugar else 0.0,
            "sodium": base_nutrients.sodium * scale_factor if base_nutrients.sodium else 0.0,
        }

        logger.debug(
            "Nutrients scaled",
            extra={
                "serving_size_g": serving_size,
                "quantity_g": quantity_g,
                "scale_factor": scale_factor,
                "calories": scaled_nutrients_dict["calories"],
            },
        )

        # 4. Create Meal aggregate using factory
        food_dict = {
            "label": product.name,
            "display_name": product.display_name(),
            "quantity_g": quantity_g,
            "confidence": 1.0,  # Barcode = 100% confidence
            "category": None,  # Not available for barcode products
        }

        meal = self._factory.create_from_analysis(
            user_id=user_id,
            items=[(food_dict, scaled_nutrients_dict)],
            source="BARCODE",
            timestamp=timestamp or datetime.now(timezone.utc),
            meal_type=meal_type,
            analysis_id=f"barcode_{uuid4().hex[:12]}",
        )

        # 5. Add barcode metadata to entry
        # Note: This assumes MealEntry has a barcode field
        # If not, this step can be skipped or stored in notes
        # TODO: Add barcode field to MealEntry or store in notes
        # if meal.entries:
        #     meal.entries[0].barcode = barcode

        logger.info(
            "Barcode analysis complete",
            extra={
                "meal_id": str(meal.id),
                "product_name": product.name,
                "total_calories": meal.total_calories,
            },
        )

        return meal
