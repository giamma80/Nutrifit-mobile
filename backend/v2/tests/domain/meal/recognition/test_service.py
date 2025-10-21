"""
Tests for food recognition service.

Test AI-powered food identification from photos.
"""

from typing import Any
import pytest
from unittest.mock import AsyncMock
from v2.domain.meal.recognition.service import FoodRecognitionService
from v2.domain.meal.recognition.models import (
    RecognitionRequest,
    RecognitionStatus,
)


class TestFoodRecognitionService:
    """Test FoodRecognitionService."""

    @pytest.fixture
    def mock_openai_client(self) -> Any:
        """Create mock OpenAI client."""
        client = AsyncMock()
        client.recognize_food = AsyncMock()
        return client

    @pytest.fixture
    def service(self, mock_openai_client: Any) -> Any:
        """Create service with mocked client."""
        return FoodRecognitionService(min_confidence=0.5, openai_client=mock_openai_client)

    @pytest.mark.asyncio
    async def test_recognize_success(self, service: Any, mock_openai_client: Any) -> None:
        """Test successful food recognition."""
        # Mock OpenAI response
        mock_openai_client.recognize_food.return_value = {
            "dish_name": "Pasta Carbonara",
            "items": [
                {
                    "label": "pasta",
                    "display_name": "Spaghetti Carbonara",
                    "quantity_g": 200.0,
                    "confidence": 0.95,
                    "category": "grain",
                },
                {
                    "label": "bacon",
                    "display_name": "Crispy Bacon",
                    "quantity_g": 50.0,
                    "confidence": 0.88,
                    "category": "protein",
                },
            ],
        }

        # Create request
        request = RecognitionRequest(
            image_url="https://example.com/pasta.jpg",
            user_id="user_123",
            dish_hint="pasta",
        )

        # Recognize
        result = await service.recognize(request)

        # Verify result
        assert result.status == RecognitionStatus.SUCCESS
        assert len(result.items) == 2
        assert result.items[0].label == "pasta"
        assert result.items[0].quantity_g == 200.0
        assert result.items[1].label == "bacon"
        assert result.confidence > 0.9
        assert result.dish_name == "Pasta Carbonara"
        assert result.processing_time_ms >= 0  # Mock is instant

    @pytest.mark.asyncio
    async def test_recognize_filters_low_confidence(
        self, service: Any, mock_openai_client: Any
    ) -> None:
        """Test confidence filtering."""
        # Mock response with low confidence item
        mock_openai_client.recognize_food.return_value = {
            "items": [
                {
                    "label": "chicken",
                    "display_name": "Chicken",
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

        request = RecognitionRequest(
            image_url="https://example.com/meal.jpg",
            user_id="user_123",
            dish_hint=None,
        )

        result = await service.recognize(request)

        # Only high confidence item should be included
        assert result.status == RecognitionStatus.PARTIAL
        assert len(result.items) == 1
        assert result.items[0].label == "chicken"

    @pytest.mark.asyncio
    async def test_recognize_no_items(self, service: Any, mock_openai_client: Any) -> None:
        """Test recognition with no items found."""
        mock_openai_client.recognize_food.return_value = {"items": []}

        request = RecognitionRequest(
            image_url="https://example.com/empty.jpg",
            user_id="user_123",
            dish_hint=None,
        )

        result = await service.recognize(request)

        assert result.status == RecognitionStatus.FAILED
        assert len(result.items) == 0
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_recognize_api_error(self, service: Any, mock_openai_client: Any) -> None:
        """Test handling of API errors."""
        mock_openai_client.recognize_food.side_effect = Exception("API Error")

        request = RecognitionRequest(
            image_url="https://example.com/meal.jpg",
            user_id="user_123",
            dish_hint=None,
        )

        result = await service.recognize(request)

        assert result.status == RecognitionStatus.FAILED
        assert len(result.items) == 0
        assert "API Error" in result.raw_response

    @pytest.mark.asyncio
    async def test_recognize_batch(self, service: Any, mock_openai_client: Any) -> None:
        """Test batch recognition."""
        mock_openai_client.recognize_food.return_value = {
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

        requests = [
            RecognitionRequest(
                image_url="https://example.com/meal1.jpg",
                user_id="user_123",
                dish_hint=None,
            ),
            RecognitionRequest(
                image_url="https://example.com/meal2.jpg",
                user_id="user_123",
                dish_hint=None,
            ),
        ]

        results = await service.recognize_batch(requests)

        assert len(results) == 2
        assert all(r.status == RecognitionStatus.SUCCESS for r in results)
        assert mock_openai_client.recognize_food.call_count == 2

    def test_parse_items_valid(self, service: Any) -> None:
        """Test parsing valid items."""
        raw_items = [
            {
                "label": "chicken",
                "display_name": "Grilled Chicken",
                "quantity_g": 150.0,
                "confidence": 0.92,
                "category": "protein",
            },
            {
                "label": "rice",
                "display_name": "White Rice",
                "quantity_g": 200.0,
                "confidence": 0.88,
                "category": "grain",
            },
        ]

        items = service._parse_items(raw_items)

        assert len(items) == 2
        assert items[0].label == "chicken"
        assert items[1].label == "rice"

    def test_parse_items_invalid(self, service: Any) -> None:
        """Test parsing with invalid items (skipped)."""
        raw_items = [
            {
                "label": "chicken",
                "display_name": "Grilled Chicken",
                "quantity_g": 150.0,
                "confidence": 0.92,
            },
            {
                "label": "invalid",
                "quantity_g": "not_a_number",
                "confidence": 0.5,
            },
        ]

        items = service._parse_items(raw_items)

        # Invalid item should be skipped
        assert len(items) == 1
        assert items[0].label == "chicken"

    def test_parse_items_missing_display_name(self, service: Any) -> None:
        """Test parsing items without display_name."""
        raw_items = [
            {
                "label": "apple",
                "quantity_g": 150.0,
                "confidence": 0.9,
            }
        ]

        items = service._parse_items(raw_items)

        assert len(items) == 1
        # Should use label as display_name fallback
        assert items[0].display_name == "apple"
