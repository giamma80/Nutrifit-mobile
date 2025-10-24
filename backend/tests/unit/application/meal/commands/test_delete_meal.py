"""Unit tests for DeleteMealCommand and handler.

Tests focus on:
- Successful deletion with authorization
- Meal not found scenarios
- Permission errors
- Event publishing
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from application.meal.commands.delete_meal import (
    DeleteMealCommand,
    DeleteMealCommandHandler,
)
from domain.meal.core.entities.meal import Meal
from domain.meal.core.events.meal_deleted import MealDeleted


@pytest.fixture
def mock_repository():
    """Mock meal repository."""
    return AsyncMock()


@pytest.fixture
def mock_event_bus():
    """Mock event bus."""
    return AsyncMock()


@pytest.fixture
def handler(mock_repository, mock_event_bus):
    """Create handler with mocked dependencies."""
    return DeleteMealCommandHandler(
        repository=mock_repository,
        event_bus=mock_event_bus
    )


@pytest.fixture
def sample_meal():
    """Create sample meal for testing."""
    meal_id = uuid4()
    user_id = "user123"

    # Create minimal meal (will be mocked anyway)
    meal = MagicMock(spec=Meal)
    meal.id = meal_id
    meal.user_id = user_id

    return meal


class TestDeleteMealCommand:
    """Test DeleteMealCommand dataclass."""

    def test_command_creation(self):
        """Test command can be created with required fields."""
        meal_id = uuid4()
        command = DeleteMealCommand(
            meal_id=meal_id,
            user_id="user123"
        )

        assert command.meal_id == meal_id
        assert command.user_id == "user123"

    def test_command_is_frozen(self):
        """Test command is immutable."""
        command = DeleteMealCommand(
            meal_id=uuid4(),
            user_id="user123"
        )

        with pytest.raises(AttributeError):
            command.user_id = "user456"  # type: ignore[misc]


class TestDeleteMealCommandHandler:
    """Test DeleteMealCommandHandler."""

    @pytest.mark.asyncio
    async def test_delete_meal_success(
        self,
        handler,
        mock_repository,
        mock_event_bus,
        sample_meal
    ):
        """Test successful meal deletion."""
        # Setup
        command = DeleteMealCommand(
            meal_id=sample_meal.id,
            user_id=sample_meal.user_id
        )

        mock_repository.get_by_id.return_value = sample_meal
        mock_repository.delete.return_value = True

        # Execute
        result = await handler.handle(command)

        # Assert
        assert result is True
        mock_repository.get_by_id.assert_called_once_with(
            sample_meal.id,
            sample_meal.user_id
        )
        mock_repository.delete.assert_called_once_with(
            sample_meal.id,
            sample_meal.user_id
        )

        # Verify event published
        mock_event_bus.publish.assert_called_once()
        event = mock_event_bus.publish.call_args[0][0]
        assert isinstance(event, MealDeleted)
        assert event.meal_id == sample_meal.id
        assert event.user_id == sample_meal.user_id

    @pytest.mark.asyncio
    async def test_delete_meal_not_found(
        self,
        handler,
        mock_repository,
        mock_event_bus
    ):
        """Test deletion when meal doesn't exist."""
        # Setup
        command = DeleteMealCommand(
            meal_id=uuid4(),
            user_id="user123"
        )

        mock_repository.get_by_id.return_value = None

        # Execute
        result = await handler.handle(command)

        # Assert
        assert result is False
        mock_repository.delete.assert_not_called()
        mock_event_bus.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_meal_wrong_owner(
        self,
        handler,
        mock_repository,
        sample_meal
    ):
        """Test deletion fails when user doesn't own meal."""
        # Setup
        command = DeleteMealCommand(
            meal_id=sample_meal.id,
            user_id="different_user"
        )

        # Repository should return None for unauthorized access
        mock_repository.get_by_id.return_value = None

        # Execute
        result = await handler.handle(command)

        # Assert
        assert result is False
        mock_repository.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_meal_permission_error(
        self,
        handler,
        mock_repository,
        sample_meal
    ):
        """Test permission error when meal exists but user doesn't own it."""
        # Setup
        command = DeleteMealCommand(
            meal_id=sample_meal.id,
            user_id="different_user"
        )

        # Repository returns meal (shouldn't happen in real scenario)
        mock_repository.get_by_id.return_value = sample_meal

        # Execute & Assert
        with pytest.raises(PermissionError):
            await handler.handle(command)

    @pytest.mark.asyncio
    async def test_delete_fails_no_event(
        self,
        handler,
        mock_repository,
        mock_event_bus,
        sample_meal
    ):
        """Test no event published when deletion fails."""
        # Setup
        command = DeleteMealCommand(
            meal_id=sample_meal.id,
            user_id=sample_meal.user_id
        )

        mock_repository.get_by_id.return_value = sample_meal
        mock_repository.delete.return_value = False  # Deletion failed

        # Execute
        result = await handler.handle(command)

        # Assert
        assert result is False
        mock_event_bus.publish.assert_not_called()
