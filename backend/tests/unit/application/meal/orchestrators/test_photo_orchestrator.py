"""Unit tests for PhotoOrchestrator.

Tests focus on:
- Service coordination
- Entity conversion
- Meal creation via factory
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from application.meal.orchestrators.photo_orchestrator import PhotoOrchestrator
from domain.meal.core.entities.meal import Meal
from domain.meal.recognition.entities.recognized_food import (
    RecognizedFood,
    FoodRecognitionResult
)
from domain.meal.nutrition.entities.nutrient_profile import NutrientProfile


@pytest.fixture
def mock_recognition_service():
    return AsyncMock()


@pytest.fixture
def mock_nutrition_service():
    return AsyncMock()


@pytest.fixture
def mock_meal_factory():
    return MagicMock()


@pytest.fixture
def orchestrator(mock_recognition_service, mock_nutrition_service, mock_meal_factory):
    return PhotoOrchestrator(
        recognition_service=mock_recognition_service,
        nutrition_service=mock_nutrition_service,
        meal_factory=mock_meal_factory
    )


@pytest.fixture
def sample_recognition_result():
    foods = [
        RecognizedFood(
            label="pasta",
            display_name="Spaghetti",
            quantity_g=150.0,
            confidence=0.9,
            category="grains"
        ),
        RecognizedFood(
            label="tomato_sauce",
            display_name="Salsa di pomodoro",
            quantity_g=100.0,
            confidence=0.85,
            category="vegetables"
        )
    ]
    return FoodRecognitionResult(items=foods, dish_name="Pasta al Pomodoro")


@pytest.fixture
def sample_nutrient_profile():
    return NutrientProfile(
        calories=200,
        protein=8.0,
        carbs=40.0,
        fat=2.0,
        fiber=3.0,
        sugar=2.0,
        sodium=100.0
    )


@pytest.fixture
def sample_meal():
    meal = MagicMock(spec=Meal)
    meal.id = MagicMock()
    meal.entries = [MagicMock(), MagicMock()]
    meal.total_calories = 500
    return meal


class TestPhotoOrchestrator:
    """Test PhotoOrchestrator."""

    @pytest.mark.asyncio
    async def test_analyze_success(
        self,
        orchestrator,
        mock_recognition_service,
        mock_nutrition_service,
        mock_meal_factory,
        sample_recognition_result,
        sample_nutrient_profile,
        sample_meal
    ):
        """Test successful photo analysis workflow."""
        # Setup mocks
        mock_recognition_service.recognize_from_photo.return_value = sample_recognition_result
        mock_nutrition_service.enrich.return_value = sample_nutrient_profile
        mock_meal_factory.create_from_analysis.return_value = sample_meal

        # Execute
        result = await orchestrator.analyze(
            user_id="user123",
            photo_url="https://example.com/pasta.jpg",
            dish_hint="pasta",
            meal_type="LUNCH"
        )

        # Assert
        assert result == sample_meal

        # Verify recognition called
        mock_recognition_service.recognize_from_photo.assert_called_once_with(
            photo_url="https://example.com/pasta.jpg",
            dish_hint="pasta"
        )

        # Verify enrichment called for each food (2 items)
        assert mock_nutrition_service.enrich.call_count == 2

        # Verify factory called
        mock_meal_factory.create_from_analysis.assert_called_once()
        call_args = mock_meal_factory.create_from_analysis.call_args
        assert call_args.kwargs["user_id"] == "user123"
        assert call_args.kwargs["source"] == "PHOTO"
        assert call_args.kwargs["meal_type"] == "LUNCH"
        assert len(call_args.kwargs["items"]) == 2

    @pytest.mark.asyncio
    async def test_analyze_with_defaults(
        self,
        orchestrator,
        mock_recognition_service,
        sample_recognition_result,
        mock_nutrition_service,
        sample_nutrient_profile,
        mock_meal_factory,
        sample_meal
    ):
        """Test analysis with default parameters."""
        mock_recognition_service.recognize_from_photo.return_value = sample_recognition_result
        mock_nutrition_service.enrich.return_value = sample_nutrient_profile
        mock_meal_factory.create_from_analysis.return_value = sample_meal

        await orchestrator.analyze(
            user_id="user123",
            photo_url="https://example.com/food.jpg"
        )

        # Verify defaults
        call_args = mock_meal_factory.create_from_analysis.call_args
        assert call_args.kwargs["meal_type"] == "SNACK"
        assert call_args.kwargs["photo_url"] == "https://example.com/food.jpg"
