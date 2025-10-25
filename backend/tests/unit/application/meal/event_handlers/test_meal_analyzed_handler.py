"""Unit tests for MealAnalyzedHandler."""

import pytest
from unittest.mock import patch
from uuid import uuid4

from application.meal.event_handlers.meal_analyzed_handler import MealAnalyzedHandler
from domain.meal.core.events.meal_analyzed import MealAnalyzed


@pytest.fixture
def handler() -> MealAnalyzedHandler:
    return MealAnalyzedHandler()


@pytest.fixture
def sample_event() -> MealAnalyzed:
    return MealAnalyzed.create(
        meal_id=uuid4(),
        user_id="user123",
        source="PHOTO",
        item_count=3,
        average_confidence=0.85,
    )


class TestMealAnalyzedHandler:
    """Test MealAnalyzedHandler."""

    @pytest.mark.asyncio
    async def test_handle_logs_event(
        self, handler: MealAnalyzedHandler, sample_event: MealAnalyzed
    ) -> None:
        """Test that handler logs MealAnalyzed event with correct structure."""
        with patch("application.meal.event_handlers.meal_analyzed_handler.logger") as mock_logger:
            await handler.handle(sample_event)

            # Verify logger.info was called
            mock_logger.info.assert_called_once()

            # Verify call arguments
            call_args = mock_logger.info.call_args
            assert call_args[0][0] == "meal_analyzed"

            # Verify extra fields
            extra = call_args[1]["extra"]
            assert extra["event_type"] == "MealAnalyzed"
            assert extra["event_id"] == str(sample_event.event_id)
            assert extra["meal_id"] == str(sample_event.meal_id)
            assert extra["user_id"] == "user123"
            assert extra["source"] == "PHOTO"
            assert extra["item_count"] == 3
            assert extra["average_confidence"] == 0.85

    @pytest.mark.asyncio
    async def test_handle_photo_source(self, handler: MealAnalyzedHandler) -> None:
        """Test handler with PHOTO source."""
        event = MealAnalyzed.create(
            meal_id=uuid4(),
            user_id="user123",
            source="PHOTO",
            item_count=2,
            average_confidence=0.9,
        )

        with patch("application.meal.event_handlers.meal_analyzed_handler.logger") as mock_logger:
            await handler.handle(event)

            extra = mock_logger.info.call_args[1]["extra"]
            assert extra["source"] == "PHOTO"
            assert extra["item_count"] == 2
            assert extra["average_confidence"] == 0.9

    @pytest.mark.asyncio
    async def test_handle_barcode_source(self, handler: MealAnalyzedHandler) -> None:
        """Test handler with BARCODE source."""
        event = MealAnalyzed.create(
            meal_id=uuid4(),
            user_id="user123",
            source="BARCODE",
            item_count=1,
            average_confidence=1.0,
        )

        with patch("application.meal.event_handlers.meal_analyzed_handler.logger") as mock_logger:
            await handler.handle(event)

            extra = mock_logger.info.call_args[1]["extra"]
            assert extra["source"] == "BARCODE"
            assert extra["average_confidence"] == 1.0

    @pytest.mark.asyncio
    async def test_handle_description_source(self, handler: MealAnalyzedHandler) -> None:
        """Test handler with DESCRIPTION source."""
        event = MealAnalyzed.create(
            meal_id=uuid4(),
            user_id="user123",
            source="DESCRIPTION",
            item_count=5,
            average_confidence=0.75,
        )

        with patch("application.meal.event_handlers.meal_analyzed_handler.logger") as mock_logger:
            await handler.handle(event)

            extra = mock_logger.info.call_args[1]["extra"]
            assert extra["source"] == "DESCRIPTION"
            assert extra["item_count"] == 5

    @pytest.mark.asyncio
    async def test_handle_low_confidence(self, handler: MealAnalyzedHandler) -> None:
        """Test handler with low confidence score."""
        event = MealAnalyzed.create(
            meal_id=uuid4(),
            user_id="user123",
            source="PHOTO",
            item_count=1,
            average_confidence=0.3,
        )

        with patch("application.meal.event_handlers.meal_analyzed_handler.logger") as mock_logger:
            await handler.handle(event)

            extra = mock_logger.info.call_args[1]["extra"]
            assert extra["average_confidence"] == 0.3

    @pytest.mark.asyncio
    async def test_handle_multiple_items(self, handler: MealAnalyzedHandler) -> None:
        """Test handler with many items."""
        event = MealAnalyzed.create(
            meal_id=uuid4(),
            user_id="user123",
            source="PHOTO",
            item_count=10,
            average_confidence=0.88,
        )

        with patch("application.meal.event_handlers.meal_analyzed_handler.logger") as mock_logger:
            await handler.handle(event)

            extra = mock_logger.info.call_args[1]["extra"]
            assert extra["item_count"] == 10
