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
def mock_idempotency_cache():
    return AsyncMock()


@pytest.fixture
def handler(mock_orchestrator, mock_repository, mock_event_bus, mock_idempotency_cache):
    return AnalyzeMealPhotoCommandHandler(
        orchestrator=mock_orchestrator,
        repository=mock_repository,
        event_bus=mock_event_bus,
        idempotency_cache=mock_idempotency_cache
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

    @pytest.mark.asyncio
    async def test_analyze_photo_idempotency_cache_miss(
        self,
        handler,
        mock_orchestrator,
        mock_repository,
        mock_event_bus,
        mock_idempotency_cache,
        sample_analyzed_meal
    ):
        """Test photo analysis with idempotency key - cache miss."""
        command = AnalyzeMealPhotoCommand(
            user_id="user123",
            photo_url="https://example.com/pasta.jpg",
            meal_type="LUNCH",
            idempotency_key="idem-key-123"
        )

        # Cache miss
        mock_idempotency_cache.get.return_value = None
        mock_orchestrator.analyze.return_value = sample_analyzed_meal

        result = await handler.handle(command)

        assert result == sample_analyzed_meal

        # Verify cache was checked
        mock_idempotency_cache.get.assert_called_once_with("idem-key-123")

        # Verify analysis happened (cache miss)
        mock_orchestrator.analyze.assert_called_once()
        mock_repository.save.assert_called_once()

        # Verify result was cached
        mock_idempotency_cache.set.assert_called_once_with(
            "idem-key-123",
            sample_analyzed_meal.id,
            ttl_seconds=3600
        )

    @pytest.mark.asyncio
    async def test_analyze_photo_idempotency_cache_hit(
        self,
        handler,
        mock_orchestrator,
        mock_repository,
        mock_idempotency_cache,
        sample_analyzed_meal
    ):
        """Test photo analysis with idempotency key - cache hit."""
        command = AnalyzeMealPhotoCommand(
            user_id="user123",
            photo_url="https://example.com/pasta.jpg",
            meal_type="LUNCH",
            idempotency_key="idem-key-456"
        )

        # Cache hit - return existing meal ID
        cached_meal_id = sample_analyzed_meal.id
        mock_idempotency_cache.get.return_value = cached_meal_id
        mock_repository.get_by_id.return_value = sample_analyzed_meal

        result = await handler.handle(command)

        assert result == sample_analyzed_meal

        # Verify cache was checked
        mock_idempotency_cache.get.assert_called_once_with("idem-key-456")

        # Verify meal retrieved from repository
        mock_repository.get_by_id.assert_called_once_with(
            cached_meal_id, "user123"
        )

        # Verify analysis NOT executed (idempotency)
        mock_orchestrator.analyze.assert_not_called()
        mock_repository.save.assert_not_called()

        # Verify result NOT cached again
        mock_idempotency_cache.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_analyze_photo_no_idempotency_key(
        self,
        handler,
        mock_orchestrator,
        mock_idempotency_cache,
        sample_analyzed_meal
    ):
        """Test photo analysis without idempotency key."""
        command = AnalyzeMealPhotoCommand(
            user_id="user123",
            photo_url="https://example.com/pasta.jpg",
            meal_type="LUNCH"
            # No idempotency_key
        )

        mock_orchestrator.analyze.return_value = sample_analyzed_meal

        result = await handler.handle(command)

        assert result == sample_analyzed_meal

        # Verify cache was NOT checked
        mock_idempotency_cache.get.assert_not_called()

        # Verify analysis happened
        mock_orchestrator.analyze.assert_called_once()

        # Verify result was NOT cached
        mock_idempotency_cache.set.assert_not_called()
