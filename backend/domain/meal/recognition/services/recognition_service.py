"""Domain service for AI-powered food recognition.

This service orchestrates food recognition from photos and text using
vision AI providers through the ports pattern.
"""

import logging
from typing import Optional

from domain.meal.recognition.entities.recognized_food import FoodRecognitionResult
from domain.meal.recognition.ports.vision_provider import IVisionProvider

logger = logging.getLogger(__name__)


class FoodRecognitionService:
    """
    Domain service for AI-powered food recognition.

    Delegates actual AI analysis to vision providers (e.g., OpenAI GPT-4 Vision)
    while providing domain-level orchestration and logging.

    This service follows the ports pattern:
    - Service defines business logic
    - Port (IVisionProvider) defines contract
    - Infrastructure provides implementation
    """

    def __init__(self, vision_provider: IVisionProvider):
        """
        Initialize recognition service with vision provider.

        Args:
            vision_provider: Implementation of IVisionProvider (e.g., OpenAI client)
        """
        self._vision = vision_provider

    async def recognize_from_photo(
        self, photo_url: str, dish_hint: Optional[str] = None
    ) -> FoodRecognitionResult:
        """
        Recognize food items from photo.

        Args:
            photo_url: URL of the food photo
            dish_hint: Optional hint from user about the dish
                      (helps improve recognition accuracy)

        Returns:
            FoodRecognitionResult with recognized items

        Raises:
            Exception: If vision provider fails (network, API, etc.)

        Example:
            >>> service = FoodRecognitionService(openai_provider)
            >>> result = await service.recognize_from_photo(
            ...     "https://example.com/meal.jpg",
            ...     dish_hint="Italian pasta"
            ... )
            >>> print(f"Recognized {result.item_count()} items")
            >>> print(f"Confidence: {result.confidence:.2%}")
        """
        logger.info(
            "Recognizing food from photo",
            extra={"photo_url": photo_url, "has_hint": dish_hint is not None},
        )

        try:
            result = await self._vision.analyze_photo(photo_url, dish_hint)

            logger.info(
                "Recognition complete",
                extra={
                    "item_count": result.item_count(),
                    "confidence": result.confidence,
                    "processing_time_ms": result.processing_time_ms,
                    "reliable": result.is_reliable(),
                },
            )

            return result

        except Exception as e:
            logger.error(
                "Photo recognition failed",
                extra={"photo_url": photo_url, "error": str(e)},
                exc_info=True,
            )
            raise

    async def recognize_from_text(self, description: str) -> FoodRecognitionResult:
        """
        Extract food items from text description.

        Useful when users manually describe what they ate instead of
        taking a photo.

        Args:
            description: Text description of the meal
                        (e.g., "I ate pasta with chicken and vegetables")

        Returns:
            FoodRecognitionResult with extracted items

        Raises:
            ValueError: If description is empty
            Exception: If vision provider fails (network, API, etc.)

        Example:
            >>> service = FoodRecognitionService(openai_provider)
            >>> result = await service.recognize_from_text(
            ...     "I had 150g of grilled salmon and 200g of rice"
            ... )
            >>> for item in result.items:
            ...     print(f"{item.display_name}: {item.quantity_g}g")
        """
        if not description or not description.strip():
            raise ValueError("Description cannot be empty")

        logger.info(
            "Recognizing food from text",
            extra={"text_length": len(description)},
        )

        try:
            result = await self._vision.analyze_text(description)

            logger.info(
                "Recognition complete",
                extra={
                    "item_count": result.item_count(),
                    "confidence": result.confidence,
                    "processing_time_ms": result.processing_time_ms,
                    "reliable": result.is_reliable(),
                },
            )

            return result

        except Exception as e:
            logger.error(
                "Text recognition failed",
                extra={"text_length": len(description), "error": str(e)},
                exc_info=True,
            )
            raise

    async def validate_recognition(
        self, result: FoodRecognitionResult, min_confidence: float = 0.7
    ) -> bool:
        """
        Validate if recognition result meets quality threshold.

        Args:
            result: Recognition result to validate
            min_confidence: Minimum average confidence required (default: 0.7)

        Returns:
            True if result is reliable (confidence >= threshold)

        Example:
            >>> result = await service.recognize_from_photo(photo_url)
            >>> if service.validate_recognition(result, min_confidence=0.8):
            ...     print("High quality recognition!")
            ... else:
            ...     print("Low confidence, manual review recommended")
        """
        is_valid = result.confidence >= min_confidence

        logger.info(
            "Recognition validation",
            extra={
                "confidence": result.confidence,
                "min_confidence": min_confidence,
                "is_valid": is_valid,
                "item_count": result.item_count(),
            },
        )

        return is_valid
