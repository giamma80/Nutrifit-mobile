"""Unit tests for FoodRecognitionService.

Tests service orchestration with mocked vision provider.
"""

import pytest
from typing import Optional

from domain.meal.recognition.entities import FoodRecognitionResult, RecognizedFood
from domain.meal.recognition.services import FoodRecognitionService


# Mock provider implementation for testing
class MockVisionProvider:
    """Mock vision provider for testing."""

    def __init__(
        self,
        photo_result: Optional[FoodRecognitionResult] = None,
        text_result: Optional[FoodRecognitionResult] = None,
        should_raise: bool = False,
    ):
        self.photo_result = photo_result
        self.text_result = text_result
        self.should_raise = should_raise
        self.photo_calls: list[tuple[str, Optional[str]]] = []
        self.text_calls: list[str] = []

    async def analyze_photo(
        self, photo_url: str, hint: Optional[str] = None
    ) -> FoodRecognitionResult:
        self.photo_calls.append((photo_url, hint))
        if self.should_raise:
            raise Exception("Vision API error")
        if self.photo_result is None:
            raise ValueError("photo_result not configured in mock")
        return self.photo_result

    async def analyze_text(self, description: str) -> FoodRecognitionResult:
        self.text_calls.append(description)
        if self.should_raise:
            raise Exception("Vision API error")
        if self.text_result is None:
            raise ValueError("text_result not configured in mock")
        return self.text_result


class TestRecognizeFromPhoto:
    """Test suite for recognize_from_photo method."""

    @pytest.mark.asyncio
    async def test_recognizes_photo_successfully(self) -> None:
        """Test successful photo recognition."""
        mock_result = FoodRecognitionResult(
            items=[
                RecognizedFood("pasta", "Spaghetti", 150.0, 0.92),
                RecognizedFood("chicken", "Chicken Breast", 120.0, 0.88),
            ],
            processing_time_ms=1200,
        )

        provider = MockVisionProvider(photo_result=mock_result)
        service = FoodRecognitionService(provider)

        result = await service.recognize_from_photo("https://example.com/food.jpg")

        assert result.item_count() == 2
        assert result.confidence == 0.9  # (0.92 + 0.88) / 2

    @pytest.mark.asyncio
    async def test_passes_photo_url_to_provider(self) -> None:
        """Test that photo URL is passed to provider."""
        mock_result = FoodRecognitionResult(
            items=[RecognizedFood("pasta", "Pasta", 150.0, 0.9)]
        )

        provider = MockVisionProvider(photo_result=mock_result)
        service = FoodRecognitionService(provider)

        await service.recognize_from_photo("https://example.com/meal.jpg")

        assert len(provider.photo_calls) == 1
        assert provider.photo_calls[0][0] == "https://example.com/meal.jpg"

    @pytest.mark.asyncio
    async def test_passes_hint_to_provider(self) -> None:
        """Test that hint is passed to provider."""
        mock_result = FoodRecognitionResult(
            items=[RecognizedFood("pasta", "Pasta", 150.0, 0.9)]
        )

        provider = MockVisionProvider(photo_result=mock_result)
        service = FoodRecognitionService(provider)

        await service.recognize_from_photo(
            "https://example.com/meal.jpg", dish_hint="Italian pasta"
        )

        assert provider.photo_calls[0][1] == "Italian pasta"

    @pytest.mark.asyncio
    async def test_passes_none_hint_when_not_provided(self) -> None:
        """Test that hint is None when not provided."""
        mock_result = FoodRecognitionResult(
            items=[RecognizedFood("pasta", "Pasta", 150.0, 0.9)]
        )

        provider = MockVisionProvider(photo_result=mock_result)
        service = FoodRecognitionService(provider)

        await service.recognize_from_photo("https://example.com/meal.jpg")

        assert provider.photo_calls[0][1] is None

    @pytest.mark.asyncio
    async def test_raises_exception_on_provider_failure(self) -> None:
        """Test that provider exceptions are propagated."""
        provider = MockVisionProvider(should_raise=True)
        service = FoodRecognitionService(provider)

        with pytest.raises(Exception, match="Vision API error"):
            await service.recognize_from_photo("https://example.com/meal.jpg")


class TestRecognizeFromText:
    """Test suite for recognize_from_text method."""

    @pytest.mark.asyncio
    async def test_recognizes_text_successfully(self) -> None:
        """Test successful text recognition."""
        mock_result = FoodRecognitionResult(
            items=[
                RecognizedFood("chicken", "Grilled Chicken", 150.0, 0.85),
                RecognizedFood("rice", "White Rice", 200.0, 0.9),
            ],
            processing_time_ms=800,
        )

        provider = MockVisionProvider(text_result=mock_result)
        service = FoodRecognitionService(provider)

        result = await service.recognize_from_text("I had grilled chicken and rice")

        assert result.item_count() == 2
        assert result.confidence == 0.875  # (0.85 + 0.9) / 2

    @pytest.mark.asyncio
    async def test_passes_description_to_provider(self) -> None:
        """Test that description is passed to provider."""
        mock_result = FoodRecognitionResult(
            items=[RecognizedFood("pasta", "Pasta", 150.0, 0.9)]
        )

        provider = MockVisionProvider(text_result=mock_result)
        service = FoodRecognitionService(provider)

        description = "I ate 150g of pasta"
        await service.recognize_from_text(description)

        assert len(provider.text_calls) == 1
        assert provider.text_calls[0] == description

    @pytest.mark.asyncio
    async def test_raises_if_description_empty(self) -> None:
        """Test that empty description raises ValueError."""
        mock_result = FoodRecognitionResult(
            items=[RecognizedFood("pasta", "Pasta", 150.0, 0.9)]
        )

        provider = MockVisionProvider(text_result=mock_result)
        service = FoodRecognitionService(provider)

        with pytest.raises(ValueError, match="Description cannot be empty"):
            await service.recognize_from_text("")

    @pytest.mark.asyncio
    async def test_raises_if_description_whitespace_only(self) -> None:
        """Test that whitespace-only description raises ValueError."""
        mock_result = FoodRecognitionResult(
            items=[RecognizedFood("pasta", "Pasta", 150.0, 0.9)]
        )

        provider = MockVisionProvider(text_result=mock_result)
        service = FoodRecognitionService(provider)

        with pytest.raises(ValueError, match="Description cannot be empty"):
            await service.recognize_from_text("   ")

    @pytest.mark.asyncio
    async def test_raises_exception_on_provider_failure(self) -> None:
        """Test that provider exceptions are propagated."""
        provider = MockVisionProvider(should_raise=True)
        service = FoodRecognitionService(provider)

        with pytest.raises(Exception, match="Vision API error"):
            await service.recognize_from_text("I ate pasta")


class TestValidateRecognition:
    """Test suite for validate_recognition method."""

    @pytest.mark.asyncio
    async def test_validates_high_confidence_result(self) -> None:
        """Test validation passes for high confidence."""
        result = FoodRecognitionResult(
            items=[RecognizedFood("pasta", "Pasta", 150.0, 0.9)]
        )

        provider = MockVisionProvider()
        service = FoodRecognitionService(provider)

        is_valid = await service.validate_recognition(result)

        assert is_valid is True

    @pytest.mark.asyncio
    async def test_validates_low_confidence_result(self) -> None:
        """Test validation fails for low confidence."""
        result = FoodRecognitionResult(
            items=[RecognizedFood("mystery", "Unknown", 100.0, 0.5)]
        )

        provider = MockVisionProvider()
        service = FoodRecognitionService(provider)

        is_valid = await service.validate_recognition(result)

        assert is_valid is False

    @pytest.mark.asyncio
    async def test_validates_with_custom_threshold(self) -> None:
        """Test validation with custom min_confidence."""
        result = FoodRecognitionResult(
            items=[RecognizedFood("pasta", "Pasta", 150.0, 0.75)]
        )

        provider = MockVisionProvider()
        service = FoodRecognitionService(provider)

        # Should pass with default threshold (0.7)
        is_valid_default = await service.validate_recognition(result)
        assert is_valid_default is True

        # Should fail with higher threshold (0.8)
        is_valid_high = await service.validate_recognition(result, min_confidence=0.8)
        assert is_valid_high is False

    @pytest.mark.asyncio
    async def test_validates_boundary_at_threshold(self) -> None:
        """Test validation boundary at exact threshold."""
        result = FoodRecognitionResult(
            items=[RecognizedFood("pasta", "Pasta", 150.0, 0.7)]
        )

        provider = MockVisionProvider()
        service = FoodRecognitionService(provider)

        # Should pass when confidence equals threshold (>=)
        is_valid = await service.validate_recognition(result, min_confidence=0.7)
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_validates_result_with_multiple_items(self) -> None:
        """Test validation with multiple items (uses average confidence)."""
        result = FoodRecognitionResult(
            items=[
                RecognizedFood("food1", "Food 1", 100.0, 0.9),
                RecognizedFood("food2", "Food 2", 100.0, 0.6),
            ]
        )
        # Average confidence: 0.75

        provider = MockVisionProvider()
        service = FoodRecognitionService(provider)

        # Should pass with threshold 0.7
        is_valid = await service.validate_recognition(result, min_confidence=0.7)
        assert is_valid is True

        # Should fail with threshold 0.8
        is_valid_high = await service.validate_recognition(result, min_confidence=0.8)
        assert is_valid_high is False
