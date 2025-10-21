"""
Tests for text extraction service.

Test AI-powered food extraction from text descriptions.
"""

from typing import Any
import pytest
from unittest.mock import AsyncMock
from v2.domain.meal.recognition.text_extractor import (
    TextExtractionService,
)
from v2.domain.meal.recognition.models import RecognitionStatus


class TestTextExtractionService:
    """Test TextExtractionService."""

    @pytest.fixture
    def mock_openai_client(self) -> Any:
        """Create mock OpenAI client."""
        client = AsyncMock()
        client.extract_foods_from_text = AsyncMock()
        return client

    @pytest.fixture
    def service(self, mock_openai_client: Any) -> Any:
        """Create service with mocked client."""
        return TextExtractionService(min_confidence=0.5, openai_client=mock_openai_client)

    @pytest.mark.asyncio
    async def test_extract_success(self, service: Any, mock_openai_client: Any) -> None:
        """Test successful food extraction."""
        # Mock OpenAI response
        mock_openai_client.extract_foods_from_text.return_value = {
            "dish_name": "Italian Pasta Meal",
            "items": [
                {
                    "label": "pasta",
                    "display_name": "Spaghetti Carbonara",
                    "quantity_g": 200.0,
                    "confidence": 0.95,
                    "category": "grain",
                },
                {
                    "label": "salad",
                    "display_name": "Mixed Green Salad",
                    "quantity_g": 100.0,
                    "confidence": 0.88,
                    "category": "vegetable",
                },
            ],
        }

        # Extract
        result = await service.extract(
            description="I had pasta carbonara and green salad",
            user_id="user_123",
        )

        # Verify result
        assert result.status == RecognitionStatus.SUCCESS
        assert len(result.items) == 2
        assert result.items[0].label == "pasta"
        assert result.items[0].quantity_g == 200.0
        assert result.items[1].label == "salad"
        assert result.confidence > 0.9
        assert result.dish_name == "Italian Pasta Meal"
        assert result.processing_time_ms >= 0  # Mock is instant

    @pytest.mark.asyncio
    async def test_extract_filters_low_confidence(
        self, service: Any, mock_openai_client: Any
    ) -> None:
        """Test confidence filtering."""
        # Mock response with low confidence item
        mock_openai_client.extract_foods_from_text.return_value = {
            "items": [
                {
                    "label": "chicken",
                    "display_name": "Chicken Breast",
                    "quantity_g": 150.0,
                    "confidence": 0.9,
                    "category": "protein",
                },
                {
                    "label": "unknown",
                    "display_name": "Unknown Item",
                    "quantity_g": 50.0,
                    "confidence": 0.3,
                    "category": "unknown",
                },
            ],
        }

        result = await service.extract(
            description="chicken and something else",
            user_id="user_123",
        )

        # Only high confidence item should be included
        assert result.status == RecognitionStatus.PARTIAL
        assert len(result.items) == 1
        assert result.items[0].label == "chicken"

    @pytest.mark.asyncio
    async def test_extract_no_items(self, service: Any, mock_openai_client: Any) -> None:
        """Test extraction with no items found."""
        mock_openai_client.extract_foods_from_text.return_value = {"items": []}

        result = await service.extract(description="nothing to eat", user_id="user_123")

        assert result.status == RecognitionStatus.FAILED
        assert len(result.items) == 0
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_extract_api_error(self, service: Any, mock_openai_client: Any) -> None:
        """Test handling of API errors."""
        mock_openai_client.extract_foods_from_text.side_effect = Exception("API Error")

        result = await service.extract(description="pasta and salad", user_id="user_123")

        assert result.status == RecognitionStatus.FAILED
        assert len(result.items) == 0
        assert "API Error" in result.raw_response

    @pytest.mark.asyncio
    async def test_extract_batch(self, service: Any, mock_openai_client: Any) -> None:
        """Test batch extraction."""
        mock_openai_client.extract_foods_from_text.return_value = {
            "items": [
                {
                    "label": "apple",
                    "display_name": "Apple",
                    "quantity_g": 150.0,
                    "confidence": 0.95,
                    "category": "fruit",
                }
            ],
        }

        descriptions = [
            "I ate an apple",
            "Had an apple for snack",
        ]

        results = await service.extract_batch(descriptions, "user_123")

        assert len(results) == 2
        assert all(r.status == RecognitionStatus.SUCCESS for r in results)
        assert mock_openai_client.extract_foods_from_text.call_count == 2

    def test_parse_items_valid(self, service: Any) -> None:
        """Test parsing valid items."""
        raw_items = [
            {
                "label": "pasta",
                "display_name": "Spaghetti",
                "quantity_g": 200.0,
                "confidence": 0.92,
                "category": "grain",
            },
            {
                "label": "chicken",
                "display_name": "Grilled Chicken",
                "quantity_g": 150.0,
                "confidence": 0.88,
                "category": "protein",
            },
        ]

        items = service._parse_items(raw_items)

        assert len(items) == 2
        assert items[0].label == "pasta"
        assert items[1].label == "chicken"

    def test_parse_items_with_defaults(self, service: Any) -> None:
        """Test parsing items with default values."""
        raw_items = [
            {
                "label": "apple",
                # Missing display_name, quantity_g, confidence
            }
        ]

        items = service._parse_items(raw_items)

        assert len(items) == 1
        assert items[0].label == "apple"
        assert items[0].quantity_g == 100.0  # Default
        assert items[0].confidence == 0.0  # Default
        assert items[0].display_name == "apple"  # Uses label as fallback
