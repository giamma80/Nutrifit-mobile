"""Unit tests for ConfirmAnalysisCommand and handler."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from application.meal.commands.confirm_analysis import (
    ConfirmAnalysisCommand,
    ConfirmAnalysisCommandHandler,
)
from domain.meal.core.entities.meal import Meal
from domain.meal.core.events.meal_confirmed import MealConfirmed
from domain.meal.core.exceptions.domain_errors import MealNotFoundError


@pytest.fixture
def mock_repository():
    return AsyncMock()


@pytest.fixture
def mock_event_bus():
    return AsyncMock()


@pytest.fixture
def handler(mock_repository, mock_event_bus):
    return ConfirmAnalysisCommandHandler(repository=mock_repository, event_bus=mock_event_bus)


@pytest.fixture
def sample_meal_with_entries():
    meal = MagicMock(spec=Meal)
    meal.id = uuid4()
    meal.user_id = "user123"
    meal.updated_at = MagicMock()
    meal.total_calories = 500

    # Mock 3 entries
    entry1 = MagicMock()
    entry1.id = uuid4()
    entry2 = MagicMock()
    entry2.id = uuid4()
    entry3 = MagicMock()
    entry3.id = uuid4()

    meal.entries = [entry1, entry2, entry3]
    meal.remove_entry = MagicMock()

    return meal


class TestConfirmAnalysisCommandHandler:
    """Test ConfirmAnalysisCommandHandler."""

    @pytest.mark.asyncio
    async def test_confirm_all_entries(
        self, handler, mock_repository, mock_event_bus, sample_meal_with_entries
    ):
        """Test confirming all entries."""
        meal = sample_meal_with_entries
        command = ConfirmAnalysisCommand(
            meal_id=meal.id, user_id=meal.user_id, confirmed_entry_ids=[e.id for e in meal.entries]
        )

        mock_repository.get_by_id.return_value = meal

        result = await handler.handle(command)

        assert result == meal
        meal.remove_entry.assert_not_called()
        mock_repository.save.assert_called_once_with(meal)

        # Verify event
        mock_event_bus.publish.assert_called_once()
        event = mock_event_bus.publish.call_args[0][0]
        assert isinstance(event, MealConfirmed)
        assert event.confirmed_entry_count == 3
        assert event.rejected_entry_count == 0

    @pytest.mark.asyncio
    async def test_confirm_some_entries(
        self, handler, mock_repository, mock_event_bus, sample_meal_with_entries
    ):
        """Test confirming only some entries."""
        meal = sample_meal_with_entries
        confirmed_ids = [meal.entries[0].id, meal.entries[1].id]
        third_entry_id = meal.entries[2].id

        # Simulate remove_entry behavior
        def remove_entry_side_effect(entry_id):
            meal.entries = [e for e in meal.entries if e.id != entry_id]

        meal.remove_entry.side_effect = remove_entry_side_effect

        command = ConfirmAnalysisCommand(
            meal_id=meal.id, user_id=meal.user_id, confirmed_entry_ids=confirmed_ids
        )

        mock_repository.get_by_id.return_value = meal

        result = await handler.handle(command)

        assert result == meal
        assert len(meal.entries) == 2
        meal.remove_entry.assert_called_once_with(third_entry_id)

    @pytest.mark.asyncio
    async def test_confirm_meal_not_found(self, handler, mock_repository):
        """Test confirmation fails when meal not found."""
        command = ConfirmAnalysisCommand(
            meal_id=uuid4(), user_id="user123", confirmed_entry_ids=[uuid4()]
        )

        mock_repository.get_by_id.return_value = None

        with pytest.raises(MealNotFoundError):
            await handler.handle(command)

    @pytest.mark.asyncio
    async def test_confirm_last_entry_cannot_be_removed(
        self, handler, mock_repository, mock_event_bus
    ):
        """Test that last entry cannot be removed (domain invariant)."""
        meal = MagicMock(spec=Meal)
        meal.id = uuid4()
        meal.user_id = "user123"
        meal.updated_at = MagicMock()
        meal.total_calories = 300

        # Only 1 entry
        entry1 = MagicMock()
        entry1.id = uuid4()
        meal.entries = [entry1]

        # Simulate domain invariant: cannot remove last entry
        meal.remove_entry.side_effect = ValueError("Cannot remove last entry from meal")

        # Try to confirm empty list (remove all entries)
        command = ConfirmAnalysisCommand(
            meal_id=meal.id, user_id=meal.user_id, confirmed_entry_ids=[]
        )

        mock_repository.get_by_id.return_value = meal

        # Should handle the ValueError gracefully and still save/publish
        result = await handler.handle(command)

        assert result == meal
        meal.remove_entry.assert_called_once_with(entry1.id)
        mock_repository.save.assert_called_once_with(meal)

        # Event still published despite warning
        mock_event_bus.publish.assert_called_once()
        event = mock_event_bus.publish.call_args[0][0]
        assert isinstance(event, MealConfirmed)
