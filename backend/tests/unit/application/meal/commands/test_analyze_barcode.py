"""Unit tests for AnalyzeMealBarcodeCommand and handler."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from application.meal.commands.analyze_barcode import (
    AnalyzeMealBarcodeCommand,
    AnalyzeMealBarcodeCommandHandler,
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
    return AnalyzeMealBarcodeCommandHandler(
        orchestrator=mock_orchestrator,
        repository=mock_repository,
        event_bus=mock_event_bus
    )


@pytest.fixture
def sample_barcode_meal():
    meal = MagicMock(spec=Meal)
    meal.id = uuid4()
    meal.user_id = "user123"

    entry = MagicMock()
    entry.display_name = "Nutella 350g"
    meal.entries = [entry]
    meal.total_calories = 220
    return meal


class TestAnalyzeMealBarcodeCommandHandler:
    """Test AnalyzeMealBarcodeCommandHandler."""

    @pytest.mark.asyncio
    async def test_analyze_barcode_success(
        self,
        handler,
        mock_orchestrator,
        mock_repository,
        mock_event_bus,
        sample_barcode_meal
    ):
        """Test successful barcode analysis."""
        command = AnalyzeMealBarcodeCommand(
            user_id="user123",
            barcode="8001505005707",
            quantity_g=150.0,
            meal_type="SNACK"
        )

        mock_orchestrator.analyze.return_value = sample_barcode_meal

        result = await handler.handle(command)

        assert result == sample_barcode_meal

        # Verify orchestrator called correctly
        mock_orchestrator.analyze.assert_called_once_with(
            user_id="user123",
            barcode="8001505005707",
            quantity_g=150.0,
            meal_type="SNACK"
        )

        # Verify meal persisted
        mock_repository.save.assert_called_once_with(sample_barcode_meal)

        # Verify event published
        mock_event_bus.publish.assert_called_once()
        event = mock_event_bus.publish.call_args[0][0]
        assert isinstance(event, MealAnalyzed)
        assert event.meal_id == sample_barcode_meal.id
        assert event.source == "BARCODE"
        assert event.item_count == 1
        assert event.average_confidence == 1.0  # Barcode = 100%

    @pytest.mark.asyncio
    async def test_analyze_barcode_with_defaults(
        self,
        handler,
        mock_orchestrator,
        sample_barcode_meal
    ):
        """Test barcode analysis with default meal_type."""
        command = AnalyzeMealBarcodeCommand(
            user_id="user123",
            barcode="8001505005707",
            quantity_g=150.0
        )

        mock_orchestrator.analyze.return_value = sample_barcode_meal

        await handler.handle(command)

        # Verify defaults used
        call_args = mock_orchestrator.analyze.call_args
        assert call_args.kwargs["meal_type"] == "SNACK"
