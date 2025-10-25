"""Unit tests for MealConfirmedHandler."""

import pytest
from unittest.mock import patch
from uuid import uuid4

from application.meal.event_handlers.meal_confirmed_handler import MealConfirmedHandler
from domain.meal.core.events.meal_confirmed import MealConfirmed


@pytest.fixture
def handler() -> MealConfirmedHandler:
    return MealConfirmedHandler()


@pytest.fixture
def sample_event() -> MealConfirmed:
    return MealConfirmed.create(
        meal_id=uuid4(),
        user_id="user123",
        confirmed_entry_count=2,
        rejected_entry_count=1,
    )


class TestMealConfirmedHandler:
    """Test MealConfirmedHandler."""

    @pytest.mark.asyncio
    async def test_handle_logs_event(
        self, handler: MealConfirmedHandler, sample_event: MealConfirmed
    ) -> None:
        """Test that handler logs MealConfirmed event with correct structure."""
        with patch("application.meal.event_handlers.meal_confirmed_handler.logger") as mock_logger:
            await handler.handle(sample_event)

            # Verify logger.info was called
            mock_logger.info.assert_called_once()

            # Verify call arguments
            call_args = mock_logger.info.call_args
            assert call_args[0][0] == "meal_confirmed"

            # Verify extra fields
            extra = call_args[1]["extra"]
            assert extra["event_type"] == "MealConfirmed"
            assert extra["event_id"] == str(sample_event.event_id)
            assert extra["meal_id"] == str(sample_event.meal_id)
            assert extra["user_id"] == "user123"
            assert extra["confirmed_entry_count"] == 2
            assert extra["rejected_entry_count"] == 1
            assert extra["total_entries"] == 3
            assert extra["acceptance_rate"] == 0.67

    @pytest.mark.asyncio
    async def test_handle_all_confirmed(self, handler: MealConfirmedHandler) -> None:
        """Test handler when all entries are confirmed."""
        event = MealConfirmed.create(
            meal_id=uuid4(),
            user_id="user123",
            confirmed_entry_count=5,
            rejected_entry_count=0,
        )

        with patch("application.meal.event_handlers.meal_confirmed_handler.logger") as mock_logger:
            await handler.handle(event)

            extra = mock_logger.info.call_args[1]["extra"]
            assert extra["confirmed_entry_count"] == 5
            assert extra["rejected_entry_count"] == 0
            assert extra["total_entries"] == 5
            assert extra["acceptance_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_handle_all_rejected(self, handler: MealConfirmedHandler) -> None:
        """Test handler when all entries are rejected."""
        event = MealConfirmed.create(
            meal_id=uuid4(),
            user_id="user123",
            confirmed_entry_count=0,
            rejected_entry_count=3,
        )

        with patch("application.meal.event_handlers.meal_confirmed_handler.logger") as mock_logger:
            await handler.handle(event)

            extra = mock_logger.info.call_args[1]["extra"]
            assert extra["confirmed_entry_count"] == 0
            assert extra["rejected_entry_count"] == 3
            assert extra["total_entries"] == 3
            assert extra["acceptance_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_handle_no_entries(self, handler: MealConfirmedHandler) -> None:
        """Test handler when no entries (edge case)."""
        event = MealConfirmed.create(
            meal_id=uuid4(),
            user_id="user123",
            confirmed_entry_count=0,
            rejected_entry_count=0,
        )

        with patch("application.meal.event_handlers.meal_confirmed_handler.logger") as mock_logger:
            await handler.handle(event)

            extra = mock_logger.info.call_args[1]["extra"]
            assert extra["total_entries"] == 0
            assert extra["acceptance_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_handle_partial_confirmation(self, handler: MealConfirmedHandler) -> None:
        """Test handler with partial confirmation."""
        event = MealConfirmed.create(
            meal_id=uuid4(),
            user_id="user123",
            confirmed_entry_count=3,
            rejected_entry_count=2,
        )

        with patch("application.meal.event_handlers.meal_confirmed_handler.logger") as mock_logger:
            await handler.handle(event)

            extra = mock_logger.info.call_args[1]["extra"]
            assert extra["confirmed_entry_count"] == 3
            assert extra["rejected_entry_count"] == 2
            assert extra["total_entries"] == 5
            assert extra["acceptance_rate"] == 0.6

    @pytest.mark.asyncio
    async def test_handle_single_entry_confirmed(self, handler: MealConfirmedHandler) -> None:
        """Test handler with single entry confirmed."""
        event = MealConfirmed.create(
            meal_id=uuid4(),
            user_id="user123",
            confirmed_entry_count=1,
            rejected_entry_count=0,
        )

        with patch("application.meal.event_handlers.meal_confirmed_handler.logger") as mock_logger:
            await handler.handle(event)

            extra = mock_logger.info.call_args[1]["extra"]
            assert extra["acceptance_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_handle_single_entry_rejected(self, handler: MealConfirmedHandler) -> None:
        """Test handler with single entry rejected."""
        event = MealConfirmed.create(
            meal_id=uuid4(),
            user_id="user123",
            confirmed_entry_count=0,
            rejected_entry_count=1,
        )

        with patch("application.meal.event_handlers.meal_confirmed_handler.logger") as mock_logger:
            await handler.handle(event)

            extra = mock_logger.info.call_args[1]["extra"]
            assert extra["acceptance_rate"] == 0.0
