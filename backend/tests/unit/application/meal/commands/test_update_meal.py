"""Unit tests for UpdateMealCommand and handler."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from application.meal.commands.update_meal import (
    UpdateMealCommand,
    UpdateMealCommandHandler,
)
from domain.meal.core.entities.meal import Meal
from domain.meal.core.events.meal_updated import MealUpdated
from domain.meal.core.exceptions.domain_errors import MealNotFoundError


@pytest.fixture
def mock_repository():
    return AsyncMock()


@pytest.fixture
def mock_event_bus():
    return AsyncMock()


@pytest.fixture
def handler(mock_repository, mock_event_bus):
    return UpdateMealCommandHandler(
        repository=mock_repository,
        event_bus=mock_event_bus
    )


@pytest.fixture
def sample_meal():
    meal = MagicMock(spec=Meal)
    meal.id = uuid4()
    meal.user_id = "user123"
    meal.meal_type = "SNACK"
    meal.notes = None
    meal.validate_invariants = MagicMock()
    return meal


class TestUpdateMealCommandHandler:
    """Test UpdateMealCommandHandler."""

    @pytest.mark.asyncio
    async def test_update_meal_success(
        self,
        handler,
        mock_repository,
        mock_event_bus,
        sample_meal
    ):
        """Test successful meal update."""
        command = UpdateMealCommand(
            meal_id=sample_meal.id,
            user_id=sample_meal.user_id,
            updates={"meal_type": "LUNCH", "notes": "Updated notes"}
        )

        mock_repository.get_by_id.return_value = sample_meal

        result = await handler.handle(command)

        assert result == sample_meal
        assert sample_meal.meal_type == "LUNCH"
        assert sample_meal.notes == "Updated notes"
        mock_repository.save.assert_called_once_with(sample_meal)

        # Verify event published
        mock_event_bus.publish.assert_called_once()
        event = mock_event_bus.publish.call_args[0][0]
        assert isinstance(event, MealUpdated)
        assert "meal_type" in event.updated_fields
        assert "notes" in event.updated_fields

    @pytest.mark.asyncio
    async def test_update_meal_not_found(
        self,
        handler,
        mock_repository
    ):
        """Test update fails when meal not found."""
        command = UpdateMealCommand(
            meal_id=uuid4(),
            user_id="user123",
            updates={"meal_type": "LUNCH"}
        )

        mock_repository.get_by_id.return_value = None

        with pytest.raises(MealNotFoundError):
            await handler.handle(command)

    @pytest.mark.asyncio
    async def test_update_no_changes_no_event(
        self,
        handler,
        mock_repository,
        mock_event_bus,
        sample_meal
    ):
        """Test no event published when no valid updates."""
        command = UpdateMealCommand(
            meal_id=sample_meal.id,
            user_id=sample_meal.user_id,
            updates={"invalid_field": "value"}
        )

        mock_repository.get_by_id.return_value = sample_meal

        await handler.handle(command)

        # Save still called but no event
        mock_repository.save.assert_called_once()
        mock_event_bus.publish.assert_not_called()
