"""
Text extraction service.

AI-powered food extraction from text descriptions using OpenAI.
"""

from __future__ import annotations

import time
from typing import Any, List, Optional
from v2.infrastructure.ai.openai_client import OpenAIClient
from v2.domain.meal.recognition.models import (
    RecognitionStatus,
    RecognizedFoodItem,
    FoodRecognitionResult,
)
from v2.domain.meal.recognition.prompts import (
    build_text_extraction_messages,
    TEXT_EXTRACTION_OUTPUT_SCHEMA,
)


class TextExtractionService:
    """
    Service for extracting foods from text descriptions.

    Uses OpenAI to parse meal descriptions and extract individual
    food items with estimated quantities. Results are USDA-compatible
    for nutrient enrichment.

    Features:
    - Text parsing with structured JSON output
    - USDA-compatible food labels
    - Quantity estimation from descriptions
    - Confidence scoring

    Example:
        >>> service = TextExtractionService()
        >>> async with service.openai_client as client:
        ...     result = await service.extract(
        ...         description="I ate pasta with chicken and salad",
        ...         user_id="user_123",
        ...     )
        >>> print(f"Extracted {len(result.items)} foods")
        >>> for item in result.items:
        ...     print(f"{item.label}: {item.quantity_g}g")
    """

    def __init__(
        self,
        min_confidence: float = 0.5,
        openai_model: str = "gpt-4o",
        openai_client: Optional[OpenAIClient] = None,
    ):
        """
        Initialize text extraction service.

        Args:
            min_confidence: Minimum confidence to include items
            openai_model: OpenAI model to use
            openai_client: Optional pre-configured client

        Example:
            >>> service = TextExtractionService(
            ...     min_confidence=0.6,
            ...     openai_model="gpt-4o",
            ... )
        """
        self.min_confidence = min_confidence
        self.openai_model = openai_model
        self.openai_client = openai_client or OpenAIClient(model=openai_model)

    async def extract(self, description: str, user_id: str) -> FoodRecognitionResult:
        """
        Extract foods from text description.

        Parses description and returns structured food items with
        USDA-compatible labels and estimated quantities.

        Args:
            description: Meal description text
            user_id: User making request

        Returns:
            FoodRecognitionResult with extracted items

        Raises:
            Exception: On API failure or invalid response

        Example:
            >>> result = await service.extract(
            ...     description="pasta carbonara 200g, salad 100g",
            ...     user_id="user_123",
            ... )
            >>> assert len(result.items) == 2
            >>> assert result.items[0].label == "pasta"
        """
        start_time = time.time()

        try:
            # Build text extraction messages with caching
            messages = build_text_extraction_messages(description=description)

            # Call OpenAI API
            raw_response = await self.openai_client.extract_foods_from_text(
                messages=messages,
                json_schema=TEXT_EXTRACTION_OUTPUT_SCHEMA,
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
                image_url=None,
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
                image_url=None,
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
            ...         "label": "pasta",
            ...         "display_name": "Spaghetti Carbonara",
            ...         "quantity_g": 200.0,
            ...         "confidence": 0.9,
            ...         "category": "grain",
            ...     }
            ... ]
            >>> items = service._parse_items(raw)
            >>> assert len(items) == 1
            >>> assert items[0].label == "pasta"
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

    async def extract_batch(
        self, descriptions: List[str], user_id: str
    ) -> List[FoodRecognitionResult]:
        """
        Extract foods from multiple text descriptions.

        Processes descriptions sequentially to respect rate limits.

        Args:
            descriptions: List of meal descriptions
            user_id: User making request

        Returns:
            List of FoodRecognitionResult (same order as input)

        Example:
            >>> descriptions = [
            ...     "pasta carbonara 200g",
            ...     "grilled chicken with rice",
            ... ]
            >>> results = await service.extract_batch(
            ...     descriptions, "user_123"
            ... )
            >>> print(f"Processed {len(results)} descriptions")
        """
        results = []
        for description in descriptions:
            result = await self.extract(description, user_id)
            results.append(result)

        return results
