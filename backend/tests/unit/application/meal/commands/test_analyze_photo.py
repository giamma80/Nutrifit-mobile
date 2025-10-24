"""Unit tests for AnalyzeMealPhotoCommand and handler."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from application.meal.commands.analyze_photo import (
    AnalyzeMealPhotoCommand,
    AnalyzeMealPhotoCommandHandler,
)
from domain.meal.core.entities.meal import Meal
from domain.meal.core.events.meal_analyzed import MealAnalyzed


@pytest.fixture
def mock_orchestrator():
    return AsyncMock()


@pytest.fixture
def mock_repository():
    return AsyncMock()


@pytest.fixture
def mock_event_bus():
    return AsyncMock()


@pytest.fixture
def handler(mock_orchestrator, mock_repository, mock_event_bus):
    return AnalyzeMealPhotoCommandHandler(
        orchestrator=mock_orchestrator,
        repository=mock_repository,
        event_bus=mock_event_bus
    )


@pytest.fixture
def sample_analyzed_meal():
    meal = MagicMock(spec=Meal)
    meal.id = uuid4()
    meal.user_id = "user123"
    meal.entries = [MagicMock(), MagicMock()]  # 2 entries
    meal.total_calories = 500
    meal.average_confidence = MagicMock(return_value=0.85)
    return meal


class TestAnalyzeMealPhotoCommandHandler:
    """Test AnalyzeMealPhotoCommandHandler."""

    @pytest.mark.asyncio
    async def test_analyze_photo_success(
        self,
        handler,
        mock_orchestrator,
        mock_repository,
        mock_event_bus,
        sample_analyzed_meal
    ):
        """Test successful photo analysis."""
        command = AnalyzeMealPhotoCommand(
            user_id="user123",
            photo_url="https://example.com/pasta.jpg",
            dish_hint="pasta",
            meal_type="LUNCH"
        )

        mock_orchestrator.analyze.return_value = sample_analyzed_meal

        result = await handler.handle(command)

        assert result == sample_analyzed_meal

        # Verify orchestrator called correctly
        mock_orchestrator.analyze.assert_called_once_with(
            user_id="user123",
            photo_url="https://example.com/pasta.jpg",
            dish_hint="pasta",
            meal_type="LUNCH"
        )

        # Verify meal persisted
        mock_repository.save.assert_called_once_with(sample_analyzed_meal)

        # Verify event published
        mock_event_bus.publish.assert_called_once()
        event = mock_event_bus.publish.call_args[0][0]
        assert isinstance(event, MealAnalyzed)
        assert event.meal_id == sample_analyzed_meal.id
        assert event.user_id == "user123"
        assert event.source == "PHOTO"
        assert event.item_count == 2

    @pytest.mark.asyncio
    async def test_analyze_photo_with_defaults(
        self,
        handler,
        mock_orchestrator,
        sample_analyzed_meal
    ):
        """Test photo analysis with default parameters."""
        command = AnalyzeMealPhotoCommand(
            user_id="user123",
            photo_url="https://example.com/food.jpg"
        )

        mock_orchestrator.analyze.return_value = sample_analyzed_meal

        await handler.handle(command)

        # Verify defaults used
        mock_orchestrator.analyze.assert_called_once_with(
            user_id="user123",
            photo_url="https://example.com/food.jpg",
            dish_hint=None,
            meal_type="SNACK"
        )
