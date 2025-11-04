"""Meal analysis orchestrator with strategy pattern.

Coordinates food recognition and nutrition enrichment for meal analysis
from multiple sources (photo, text, barcode).
"""

from datetime import datetime, timezone
from typing import Optional, List, Tuple, Dict, Any
from uuid import uuid4
import logging

from domain.meal.core.entities.meal import Meal
from domain.meal.core.factories.meal_factory import MealFactory
from domain.meal.recognition.services.recognition_service import FoodRecognitionService
from domain.meal.recognition.entities.recognized_food import FoodRecognitionResult
from domain.meal.nutrition.services.enrichment_service import NutritionEnrichmentService

logger = logging.getLogger(__name__)


class MealAnalysisOrchestrator:
    """
    Orchestrate meal analysis workflow with strategy pattern.

    Coordinates multiple domain services to transform meal input (photo/text)
    into a complete Meal aggregate with recognized foods and nutritional data.

    Flow:
    1. Recognize foods from source (photo or text via Recognition Service)
    2. Enrich each food with nutrients (Nutrition Service)
    3. Create Meal aggregate (Meal Factory)

    Strategy Pattern:
    - Photo analysis: calls recognition_service.recognize_from_photo()
    - Text analysis: calls recognition_service.recognize_from_text()

    Example:
        >>> orchestrator = MealAnalysisOrchestrator(
        ...     recognition_service,
        ...     nutrition_service,
        ...     meal_factory
        ... )
        >>> # Photo analysis
        >>> meal = await orchestrator.analyze_from_photo(
        ...     user_id="user123",
        ...     photo_url="https://example.com/pasta.jpg",
        ...     meal_type="LUNCH"
        ... )
        >>> # Text analysis
        >>> meal = await orchestrator.analyze_from_text(
        ...     user_id="user123",
        ...     text_description="150g pasta with tomato sauce",
        ...     meal_type="LUNCH"
        ... )
    """

    def __init__(
        self,
        recognition_service: FoodRecognitionService,
        nutrition_service: NutritionEnrichmentService,
        meal_factory: MealFactory,
    ):
        """
        Initialize orchestrator.

        Args:
            recognition_service: Service for food recognition (photo/text)
            nutrition_service: Service for nutrition enrichment
            meal_factory: Factory for creating Meal aggregates
        """
        self._recognition = recognition_service
        self._nutrition = nutrition_service
        self._factory = meal_factory

    async def analyze_from_photo(
        self,
        user_id: str,
        photo_url: str,
        dish_hint: Optional[str] = None,
        meal_type: str = "SNACK",
        timestamp: Optional[datetime] = None,
    ) -> Meal:
        """
        Orchestrate complete photo analysis workflow.

        Args:
            user_id: User ID who owns this meal
            photo_url: URL of the meal photo
            dish_hint: Optional hint about the dish (e.g., "pizza", "salad")
            meal_type: BREAKFAST | LUNCH | DINNER | SNACK
            timestamp: Meal timestamp (default: current time)

        Returns:
            Analyzed Meal aggregate with entries and nutritional data

        Raises:
            ValueError: If recognition fails or returns no items
            Exception: If any service fails during orchestration

        Example:
            >>> meal = await orchestrator.analyze_from_photo(
            ...     user_id="user123",
            ...     photo_url="https://example.com/pasta.jpg",
            ...     dish_hint="pasta carbonara",
            ...     meal_type="LUNCH"
            ... )
            >>> len(meal.entries) >= 1
            True
        """
        logger.info(
            "Orchestrating photo analysis",
            extra={
                "user_id": user_id,
                "photo_url": photo_url,
                "dish_hint": dish_hint,
                "meal_type": meal_type,
            },
        )

        # 1. Recognize foods from photo
        recognition_result = await self._recognition.recognize_from_photo(
            photo_url=photo_url, dish_hint=dish_hint
        )

        # 2-3. Enrich and create meal (shared logic)
        return await self._complete_analysis(
            user_id=user_id,
            recognition_result=recognition_result,
            source="PHOTO",
            meal_type=meal_type,
            timestamp=timestamp,
            photo_url=photo_url,
        )

    async def analyze_from_text(
        self,
        user_id: str,
        text_description: str,
        meal_type: str = "SNACK",
        timestamp: Optional[datetime] = None,
    ) -> Meal:
        """
        Orchestrate complete text analysis workflow.

        Args:
            user_id: User ID who owns this meal
            text_description: Text description of meal
            meal_type: BREAKFAST | LUNCH | DINNER | SNACK
            timestamp: Meal timestamp (default: current time)

        Returns:
            Analyzed Meal aggregate with entries and nutritional data

        Raises:
            ValueError: If recognition fails or returns no items
            Exception: If any service fails during orchestration

        Example:
            >>> meal = await orchestrator.analyze_from_text(
            ...     user_id="user123",
            ...     text_description="150g pasta with tomato sauce",
            ...     meal_type="LUNCH"
            ... )
            >>> len(meal.entries) >= 1
            True
        """
        logger.info(
            "Orchestrating text analysis",
            extra={
                "user_id": user_id,
                "text_length": len(text_description),
                "meal_type": meal_type,
            },
        )

        # 1. Recognize foods from text
        recognition_result = await self._recognition.recognize_from_text(
            description=text_description
        )

        # 2-3. Enrich and create meal (shared logic)
        return await self._complete_analysis(
            user_id=user_id,
            recognition_result=recognition_result,
            source="DESCRIPTION",
            meal_type=meal_type,
            timestamp=timestamp,
        )

    async def _complete_analysis(
        self,
        user_id: str,
        recognition_result: FoodRecognitionResult,
        source: str,
        meal_type: str,
        timestamp: Optional[datetime],
        photo_url: Optional[str] = None,
    ) -> Meal:
        """
        Complete analysis workflow (shared by photo and text).

        Args:
            user_id: User ID
            recognition_result: Result from recognition service
            source: "PHOTO", "DESCRIPTION", or "BARCODE"
            meal_type: Meal type
            timestamp: Meal timestamp
            photo_url: Optional photo URL (for photo source)

        Returns:
            Analyzed Meal aggregate
        """

        logger.info(
            "Recognition complete",
            extra={
                "item_count": len(recognition_result.items),
                "average_confidence": recognition_result.confidence,
                "dish_name": recognition_result.dish_name,
                "source": source,
            },
        )

        # 2. Enrich each food with nutrients
        enriched_items: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []

        for food in recognition_result.items:
            logger.debug(
                "Enriching food item",
                extra={
                    "label": food.label,
                    "quantity_g": food.quantity_g,
                },
            )

            # Get nutrients for this food
            nutrients = await self._nutrition.enrich(
                label=food.label,
                quantity_g=food.quantity_g,
                category=food.category,
            )

            # Convert to dicts for factory
            food_dict = {
                "label": food.label,
                "display_name": food.display_name,
                "quantity_g": food.quantity_g,
                "confidence": food.confidence,
                "category": food.category,
            }

            nutrients_dict = {
                "calories": nutrients.calories,
                "protein": nutrients.protein,
                "carbs": nutrients.carbs,
                "fat": nutrients.fat,
                "fiber": nutrients.fiber,
                "sugar": nutrients.sugar,
                "sodium": nutrients.sodium,
            }

            enriched_items.append((food_dict, nutrients_dict))

        logger.info(
            "Enrichment complete",
            extra={"enriched_item_count": len(enriched_items)},
        )

        # 3. Create Meal aggregate using factory
        analysis_id_prefix = source.lower()
        meal = self._factory.create_from_analysis(
            user_id=user_id,
            items=enriched_items,
            source=source,
            timestamp=timestamp or datetime.now(timezone.utc),
            meal_type=meal_type,
            photo_url=photo_url,
            analysis_id=f"{analysis_id_prefix}_{uuid4().hex[:12]}",
            dish_name=recognition_result.dish_name,
        )

        logger.info(
            f"{source} analysis complete",
            extra={
                "meal_id": str(meal.id),
                "entry_count": len(meal.entries),
                "total_calories": meal.total_calories,
                "total_protein": meal.total_protein,
            },
        )

        return meal


# Backward compatibility alias
PhotoOrchestrator = MealAnalysisOrchestrator
