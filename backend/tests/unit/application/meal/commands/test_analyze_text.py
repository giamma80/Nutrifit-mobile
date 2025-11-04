"""Unit tests for AnalyzeMealTextCommand and handler."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from application.meal.commands.analyze_text import (
    AnalyzeMealTextCommand,
    AnalyzeMealTextCommandHandler,
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
def mock_idempotency_cache():
    return AsyncMock()


@pytest.fixture
def handler(mock_orchestrator, mock_repository, mock_event_bus, mock_idempotency_cache):
    return AnalyzeMealTextCommandHandler(
        orchestrator=mock_orchestrator,
        repository=mock_repository,
        event_bus=mock_event_bus,
        idempotency_cache=mock_idempotency_cache,
    )


@pytest.fixture
def sample_analyzed_meal():
    meal = MagicMock(spec=Meal)
    meal.id = uuid4()
    meal.user_id = "user123"
    meal.entries = [MagicMock(), MagicMock()]  # 2 entries
    meal.total_calories = 450
    meal.average_confidence = MagicMock(return_value=0.80)
    return meal


class TestAnalyzeMealTextCommandHandler:
    """Test AnalyzeMealTextCommandHandler."""

    @pytest.mark.asyncio
    async def test_analyze_text_success(
        self, handler, mock_orchestrator, mock_repository, mock_event_bus, sample_analyzed_meal
    ):
        """Test successful text analysis."""
        command = AnalyzeMealTextCommand(
            user_id="user123",
            text_description="150g pasta with tomato sauce and basil",
            meal_type="LUNCH",
        )

        mock_orchestrator.analyze_from_text.return_value = sample_analyzed_meal

        result = await handler.handle(command)

        assert result == sample_analyzed_meal

        # Verify orchestrator called correctly
        mock_orchestrator.analyze_from_text.assert_called_once_with(
            user_id="user123",
            text_description="150g pasta with tomato sauce and basil",
            meal_type="LUNCH",
            timestamp=None,
        )

        # Verify meal persisted
        mock_repository.save.assert_called_once_with(sample_analyzed_meal)

        # Verify event published
        mock_event_bus.publish.assert_called_once()
        event = mock_event_bus.publish.call_args[0][0]
        assert isinstance(event, MealAnalyzed)
        assert event.meal_id == sample_analyzed_meal.id
        assert event.user_id == "user123"
        assert event.source == "DESCRIPTION"
        assert event.item_count == 2

    @pytest.mark.asyncio
    async def test_analyze_text_with_defaults(
        self, handler, mock_orchestrator, sample_analyzed_meal
    ):
        """Test text analysis with default parameters."""
        command = AnalyzeMealTextCommand(
            user_id="user123", text_description="chicken salad with vegetables"
        )

        mock_orchestrator.analyze_from_text.return_value = sample_analyzed_meal

        await handler.handle(command)

        # Verify defaults used
        mock_orchestrator.analyze_from_text.assert_called_once_with(
            user_id="user123",
            text_description="chicken salad with vegetables",
            meal_type="SNACK",
            timestamp=None,
        )

    @pytest.mark.asyncio
    async def test_analyze_text_idempotency_cache_miss(
        self,
        handler,
        mock_orchestrator,
        mock_repository,
        mock_event_bus,
        mock_idempotency_cache,
        sample_analyzed_meal,
    ):
        """Test text analysis with idempotency key - cache miss."""
        command = AnalyzeMealTextCommand(
            user_id="user123",
            text_description="grilled chicken with rice",
            meal_type="DINNER",
            idempotency_key="idem-text-123",
        )

        # Cache miss
        mock_idempotency_cache.get.return_value = None
        mock_orchestrator.analyze_from_text.return_value = sample_analyzed_meal

        result = await handler.handle(command)

        assert result == sample_analyzed_meal

        # Verify cache was checked
        mock_idempotency_cache.get.assert_called_once_with("idem-text-123")

        # Verify analysis happened (cache miss)
        mock_orchestrator.analyze_from_text.assert_called_once()
        mock_repository.save.assert_called_once()

        # Verify result was cached
        mock_idempotency_cache.set.assert_called_once_with(
            "idem-text-123", sample_analyzed_meal.id, ttl_seconds=3600
        )

    @pytest.mark.asyncio
    async def test_analyze_text_idempotency_cache_hit(
        self,
        handler,
        mock_orchestrator,
        mock_repository,
        mock_idempotency_cache,
        sample_analyzed_meal,
    ):
        """Test text analysis with idempotency key - cache hit."""
        command = AnalyzeMealTextCommand(
            user_id="user123",
            text_description="salmon with steamed vegetables",
            meal_type="DINNER",
            idempotency_key="idem-text-456",
        )

        # Cache hit - return existing meal ID
        cached_meal_id = sample_analyzed_meal.id
        mock_idempotency_cache.get.return_value = cached_meal_id
        mock_repository.get_by_id.return_value = sample_analyzed_meal

        result = await handler.handle(command)

        assert result == sample_analyzed_meal

        # Verify cache was checked
        mock_idempotency_cache.get.assert_called_once_with("idem-text-456")

        # Verify meal retrieved from repository
        mock_repository.get_by_id.assert_called_once_with(cached_meal_id, "user123")

        # Verify analysis NOT executed (idempotency)
        mock_orchestrator.analyze_from_text.assert_not_called()
        mock_repository.save.assert_not_called()

        # Verify result NOT cached again
        mock_idempotency_cache.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_analyze_text_no_idempotency_key(
        self, handler, mock_orchestrator, mock_idempotency_cache, sample_analyzed_meal
    ):
        """Test text analysis without idempotency key."""
        command = AnalyzeMealTextCommand(
            user_id="user123",
            text_description="200g brown rice with grilled fish",
            meal_type="LUNCH",
            # No idempotency_key
        )

        mock_orchestrator.analyze_from_text.return_value = sample_analyzed_meal

        result = await handler.handle(command)

        assert result == sample_analyzed_meal

        # Verify cache was NOT checked
        mock_idempotency_cache.get.assert_not_called()

        # Verify analysis happened
        mock_orchestrator.analyze_from_text.assert_called_once()

        # Verify result was NOT cached
        mock_idempotency_cache.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_analyze_text_with_timestamp(
        self, handler, mock_orchestrator, sample_analyzed_meal
    ):
        """Test text analysis with explicit timestamp."""
        from datetime import datetime

        timestamp = datetime.fromisoformat("2025-11-01T12:30:00")
        command = AnalyzeMealTextCommand(
            user_id="user123",
            text_description="scrambled eggs with toast",
            meal_type="BREAKFAST",
            timestamp=timestamp,
        )

        mock_orchestrator.analyze_from_text.return_value = sample_analyzed_meal

        await handler.handle(command)

        # Verify timestamp passed through
        mock_orchestrator.analyze_from_text.assert_called_once_with(
            user_id="user123",
            text_description="scrambled eggs with toast",
            meal_type="BREAKFAST",
            timestamp=timestamp,
        )

    @pytest.mark.asyncio
    async def test_analyze_text_empty_description_fails(self, handler, mock_orchestrator):
        """Test that empty text description is rejected."""
        command = AnalyzeMealTextCommand(
            user_id="user123",
            text_description="",  # Empty string
            meal_type="LUNCH",
        )

        # Empty description should fail at orchestrator level
        mock_orchestrator.analyze_from_text.side_effect = ValueError("Empty description")

        with pytest.raises(ValueError, match="Empty description"):
            await handler.handle(command)

    @pytest.mark.asyncio
    async def test_analyze_text_complex_description(
        self, handler, mock_orchestrator, sample_analyzed_meal
    ):
        """Test text analysis with complex multi-item description."""
        command = AnalyzeMealTextCommand(
            user_id="user123",
            text_description=(
                "Ate 200g of grilled chicken breast, 150g of quinoa, "
                "100g of steamed broccoli, and a small apple"
            ),
            meal_type="DINNER",
        )

        mock_orchestrator.analyze_from_text.return_value = sample_analyzed_meal

        result = await handler.handle(command)

        assert result == sample_analyzed_meal

        # Verify full description passed to orchestrator
        call_args = mock_orchestrator.analyze_from_text.call_args
        assert "200g of grilled chicken breast" in call_args.kwargs["text_description"]
        assert "150g of quinoa" in call_args.kwargs["text_description"]
