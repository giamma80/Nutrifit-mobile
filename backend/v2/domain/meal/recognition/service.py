"""
Food recognition service.

AI-powered food identification from photos using OpenAI Vision.
"""

from __future__ import annotations

import time
from typing import Any, List, Optional
from v2.infrastructure.ai.openai_client import OpenAIClient
from v2.domain.meal.recognition.models import (
    RecognitionStatus,
    RecognizedFoodItem,
    FoodRecognitionResult,
    RecognitionRequest,
)
from v2.domain.meal.recognition.prompts import (
    build_vision_messages,
    VISION_OUTPUT_SCHEMA,
)


class FoodRecognitionService:
    """
    Service for AI-powered food recognition from photos.

    Uses OpenAI Vision API to identify foods, estimate quantities,
    and categorize items. Results are USDA-compatible for easy
    nutrient enrichment.

    Features:
    - Vision API with structured JSON output
    - USDA-compatible food labels
    - Confidence filtering (>= 0.5 by default)
    - Performance metrics tracking

    Example:
        >>> service = FoodRecognitionService()
        >>> request = RecognitionRequest(
        ...     image_url="https://example.com/meal.jpg",
        ...     user_id="user_123",
        ...     dish_hint="pasta",
        ... )
        >>> async with service.openai_client as client:
        ...     result = await service.recognize(request)
        >>> print(f"Found {len(result.items)} foods")
        >>> print(f"Confidence: {result.confidence:.2f}")
    """

    def __init__(
        self,
        min_confidence: float = 0.5,
        openai_model: str = "gpt-4o",
        openai_client: Optional[OpenAIClient] = None,
    ):
        """
        Initialize food recognition service.

        Args:
            min_confidence: Minimum confidence to include items
            openai_model: OpenAI model to use (gpt-4o for vision)
            openai_client: Optional pre-configured client

        Example:
            >>> service = FoodRecognitionService(
            ...     min_confidence=0.6,
            ...     openai_model="gpt-4o",
            ... )
        """
        self.min_confidence = min_confidence
        self.openai_model = openai_model
        self.openai_client = openai_client or OpenAIClient(model=openai_model)

    async def recognize(self, request: RecognitionRequest) -> FoodRecognitionResult:
        """
        Recognize foods from photo.

        Sends photo to OpenAI Vision API and returns structured
        recognition result with USDA-compatible labels.

        Args:
            request: Recognition request with image URL and hint

        Returns:
            FoodRecognitionResult with recognized items

        Raises:
            Exception: On API failure or invalid response

        Example:
            >>> request = RecognitionRequest(
            ...     image_url="https://example.com/meal.jpg",
            ...     user_id="user_123",
            ...     dish_hint="sushi",
            ... )
            >>> result = await service.recognize(request)
            >>> for item in result.items:
            ...     print(f"{item.label}: {item.quantity_g}g")
        """
        start_time = time.time()

        try:
            # Build vision messages with caching optimization
            messages = build_vision_messages(image_url=request.image_url, hint=request.dish_hint)

            # Call OpenAI Vision API
            raw_response = await self.openai_client.recognize_food(
                messages=messages, json_schema=VISION_OUTPUT_SCHEMA
            )

            # Parse response into domain models
            items = self._parse_items(raw_response.get("items", []))

            # Filter by confidence
            filtered_items = [item for item in items if item.confidence >= self.min_confidence]

            # Calculate average confidence
            avg_confidence = (
                sum(item.confidence for item in filtered_items) / len(filtered_items)
                if filtered_items
                else 0.0
            )

            # Determine status
            if not filtered_items:
                status = RecognitionStatus.FAILED
            elif len(filtered_items) < len(items):
                status = RecognitionStatus.PARTIAL
            else:
                status = RecognitionStatus.SUCCESS

            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)

            return FoodRecognitionResult(
                items=filtered_items,
                dish_name=raw_response.get("dish_name"),
                image_url=raw_response.get("image_url") or request.image_url,
                confidence=round(avg_confidence, 2),
                processing_time_ms=processing_time_ms,
                status=status,
                raw_response=str(raw_response),
            )

        except Exception as e:
            # Return failed result with error details
            processing_time_ms = int((time.time() - start_time) * 1000)
            return FoodRecognitionResult(
                items=[],
                dish_name=None,
                image_url=request.image_url,
                confidence=0.0,
                processing_time_ms=processing_time_ms,
                status=RecognitionStatus.FAILED,
                raw_response=str(e),
            )

    def _parse_items(self, raw_items: List[dict[str, Any]]) -> List[RecognizedFoodItem]:
        """
        Parse raw AI response into domain models.

        Args:
            raw_items: Raw items from OpenAI response

        Returns:
            List of validated RecognizedFoodItem instances

        Example:
            >>> raw = [
            ...     {
            ...         "label": "chicken",
            ...         "display_name": "Grilled Chicken",
            ...         "quantity_g": 150.0,
            ...         "confidence": 0.92,
            ...         "category": "protein",
            ...     }
            ... ]
            >>> items = service._parse_items(raw)
            >>> assert len(items) == 1
            >>> assert items[0].label == "chicken"
        """
        items = []
        for raw_item in raw_items:
            try:
                item = RecognizedFoodItem(
                    label=raw_item.get("label", "unknown"),
                    display_name=raw_item.get("display_name", raw_item.get("label", "Unknown")),
                    quantity_g=float(raw_item.get("quantity_g", 100.0)),
                    confidence=float(raw_item.get("confidence", 0.0)),
                    category=raw_item.get("category"),
                )
                items.append(item)
            except (ValueError, TypeError):
                # Skip invalid items
                continue

        return items

    async def recognize_batch(
        self, requests: List[RecognitionRequest]
    ) -> List[FoodRecognitionResult]:
        """
        Recognize foods from multiple photos.

        Processes requests sequentially to respect rate limits.

        Args:
            requests: List of recognition requests

        Returns:
            List of FoodRecognitionResult (same order as input)

        Example:
            >>> requests = [
            ...     RecognitionRequest(
            ...         image_url="https://example.com/meal1.jpg",
            ...         user_id="user_123",
            ...     ),
            ...     RecognitionRequest(
            ...         image_url="https://example.com/meal2.jpg",
            ...         user_id="user_123",
            ...     ),
            ... ]
            >>> results = await service.recognize_batch(requests)
            >>> print(f"Processed {len(results)} photos")
        """
        results = []
        for request in requests:
            result = await self.recognize(request)
            results.append(result)

        return results
