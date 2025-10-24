"""Recognize food query - utility to test recognition capability."""

from dataclasses import dataclass
from typing import Optional
import logging

from domain.meal.recognition.entities.recognized_food import FoodRecognitionResult
from domain.meal.recognition.services.recognition_service import (
    FoodRecognitionService,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RecognizeFoodQuery:
    """
    Utility Query: Recognize food from photo or text.

    Atomic query to test recognition capability without creating meals.
    Useful for:
    - Testing AI recognition
    - Debug/troubleshooting
    - Preview before meal creation

    Attributes:
        photo_url: URL of photo to analyze (mutually exclusive with text)
        text: Text description to analyze (mutually exclusive with photo_url)
        dish_hint: Optional hint about the dish type
    """
    photo_url: Optional[str] = None
    text: Optional[str] = None
    dish_hint: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate that exactly one input is provided."""
        if not self.photo_url and not self.text:
            raise ValueError("Either photo_url or text must be provided")
        if self.photo_url and self.text:
            raise ValueError("Only one of photo_url or text can be provided")


class RecognizeFoodQueryHandler:
    """Handler for RecognizeFoodQuery."""

    def __init__(self, recognition_service: FoodRecognitionService):
        """
        Initialize handler.

        Args:
            recognition_service: Food recognition service
        """
        self._recognition = recognition_service

    async def handle(self, query: RecognizeFoodQuery) -> FoodRecognitionResult:
        """
        Execute recognition query.

        Args:
            query: RecognizeFoodQuery

        Returns:
            FoodRecognitionResult with recognized foods

        Example:
            >>> handler = RecognizeFoodQueryHandler(recognition_service)
            >>> query = RecognizeFoodQuery(
            ...     photo_url="https://example.com/pasta.jpg",
            ...     dish_hint="pasta"
            ... )
            >>> result = await handler.handle(query)
            >>> len(result.items) > 0
            True
        """
        if query.photo_url:
            logger.info(
                "Recognizing food from photo",
                extra={
                    "photo_url": query.photo_url,
                    "dish_hint": query.dish_hint,
                },
            )

            result = await self._recognition.recognize_from_photo(
                photo_url=query.photo_url,
                dish_hint=query.dish_hint
            )

        else:  # query.text
            # query.text is guaranteed to be str here due to __post_init__ validation
            text = query.text
            assert text is not None  # For mypy

            logger.info(
                "Recognizing food from text",
                extra={
                    "text": text,
                },
            )

            result = await self._recognition.recognize_from_text(
                description=text
            )

        logger.info(
            "Food recognition completed",
            extra={
                "item_count": result.item_count(),
                "avg_confidence": result.confidence,
                "total_quantity_g": result.total_quantity_g(),
            },
        )

        return result
