"""Unit tests for RecognizeFoodQuery and handler."""

import pytest
from unittest.mock import AsyncMock

from application.meal.queries.recognize_food import (
    RecognizeFoodQuery,
    RecognizeFoodQueryHandler,
)
from domain.meal.recognition.entities.recognized_food import (
    FoodRecognitionResult,
    RecognizedFood,
)


@pytest.fixture
def mock_recognition_service():
    return AsyncMock()


@pytest.fixture
def handler(mock_recognition_service):
    return RecognizeFoodQueryHandler(recognition_service=mock_recognition_service)


@pytest.fixture
def sample_recognition_result():
    foods = [
        RecognizedFood(label="pasta", display_name="Spaghetti", quantity_g=150.0, confidence=0.9),
        RecognizedFood(
            label="tomato_sauce", display_name="Tomato Sauce", quantity_g=100.0, confidence=0.85
        ),
    ]
    return FoodRecognitionResult(items=foods)


class TestRecognizeFoodQueryHandler:
    """Test RecognizeFoodQueryHandler."""

    @pytest.mark.asyncio
    async def test_recognize_from_photo(
        self, handler, mock_recognition_service, sample_recognition_result
    ):
        """Test recognizing food from photo."""
        query = RecognizeFoodQuery(photo_url="https://example.com/pasta.jpg", dish_hint="pasta")

        mock_recognition_service.recognize_from_photo.return_value = sample_recognition_result

        result = await handler.handle(query)

        assert result == sample_recognition_result
        mock_recognition_service.recognize_from_photo.assert_called_once_with(
            photo_url="https://example.com/pasta.jpg", dish_hint="pasta"
        )

    @pytest.mark.asyncio
    async def test_recognize_from_text(
        self, handler, mock_recognition_service, sample_recognition_result
    ):
        """Test recognizing food from text."""
        query = RecognizeFoodQuery(text="I ate pasta with tomato sauce")

        mock_recognition_service.recognize_from_text.return_value = sample_recognition_result

        result = await handler.handle(query)

        assert result == sample_recognition_result
        mock_recognition_service.recognize_from_text.assert_called_once_with(
            description="I ate pasta with tomato sauce"
        )

    @pytest.mark.asyncio
    async def test_recognize_from_photo_without_hint(
        self, handler, mock_recognition_service, sample_recognition_result
    ):
        """Test photo recognition without dish hint."""
        query = RecognizeFoodQuery(photo_url="https://example.com/food.jpg")

        mock_recognition_service.recognize_from_photo.return_value = (
            sample_recognition_result
        )

        await handler.handle(query)

        mock_recognition_service.recognize_from_photo.assert_called_once_with(
            photo_url="https://example.com/food.jpg", dish_hint=None
        )

    def test_recognize_food_query_validation_both_inputs(self):
        """Test validation when both photo_url and text are provided."""
        with pytest.raises(ValueError, match="Only one of photo_url or text"):
            RecognizeFoodQuery(photo_url="https://example.com/food.jpg", text="pasta")

    def test_recognize_food_query_validation_no_inputs(self):
        """Test validation when neither photo_url nor text is provided."""
        with pytest.raises(ValueError, match="Either photo_url or text must be"):
            RecognizeFoodQuery()
