"""Unit tests for GetMealHistoryQuery and handler."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, timezone, timedelta

from application.meal.queries.get_meal_history import (
    GetMealHistoryQuery,
    GetMealHistoryQueryHandler,
)
from domain.meal.core.entities.meal import Meal


@pytest.fixture
def mock_repository():
    return AsyncMock()


@pytest.fixture
def handler(mock_repository):
    return GetMealHistoryQueryHandler(repository=mock_repository)


@pytest.fixture
def sample_meals():
    """Create 5 sample meals with different types."""
    meals = []
    meal_types = ["BREAKFAST", "LUNCH", "LUNCH", "DINNER", "SNACK"]

    for i, meal_type in enumerate(meal_types):
        meal = MagicMock(spec=Meal)
        meal.id = uuid4()
        meal.user_id = "user123"
        meal.meal_type = meal_type
        meal.timestamp = datetime.now(timezone.utc) - timedelta(hours=i)
        meals.append(meal)

    return meals


class TestGetMealHistoryQueryHandler:
    """Test GetMealHistoryQueryHandler."""

    @pytest.mark.asyncio
    async def test_get_meal_history_no_filters(self, handler, mock_repository, sample_meals):
        """Test getting meal history without filters."""
        query = GetMealHistoryQuery(user_id="user123")

        mock_repository.get_by_user.return_value = sample_meals

        result = await handler.handle(query)

        assert len(result) == 5
        assert result == sample_meals
        mock_repository.get_by_user.assert_called_once_with(user_id="user123", limit=100, offset=0)

    @pytest.mark.asyncio
    async def test_get_meal_history_with_date_range(self, handler, mock_repository, sample_meals):
        """Test filtering by date range."""
        today = datetime.now(timezone.utc)
        yesterday = today - timedelta(days=1)

        query = GetMealHistoryQuery(user_id="user123", start_date=yesterday, end_date=today)

        mock_repository.get_by_user_and_date_range.return_value = sample_meals

        result = await handler.handle(query)

        assert len(result) == 5
        mock_repository.get_by_user_and_date_range.assert_called_once_with(
            user_id="user123", start_date=yesterday, end_date=today
        )

    @pytest.mark.asyncio
    async def test_get_meal_history_with_meal_type_filter(
        self, handler, mock_repository, sample_meals
    ):
        """Test filtering by meal type."""
        query = GetMealHistoryQuery(user_id="user123", meal_type="LUNCH")

        mock_repository.get_by_user.return_value = sample_meals

        result = await handler.handle(query)

        # Should only return LUNCH meals (2 out of 5)
        assert len(result) == 2
        assert all(m.meal_type == "LUNCH" for m in result)

    @pytest.mark.asyncio
    async def test_get_meal_history_with_pagination(self, handler, mock_repository, sample_meals):
        """Test pagination."""
        query = GetMealHistoryQuery(user_id="user123", limit=2, offset=1)

        mock_repository.get_by_user.return_value = sample_meals

        await handler.handle(query)

        mock_repository.get_by_user.assert_called_once_with(
            user_id="user123", limit=2, offset=1
        )

    @pytest.mark.asyncio
    async def test_get_meal_history_empty_result(self, handler, mock_repository):
        """Test empty result."""
        query = GetMealHistoryQuery(user_id="user123")

        mock_repository.get_by_user.return_value = []

        meals = await handler.handle(query)

        assert meals == []

    @pytest.mark.asyncio
    async def test_get_meal_history_combined_filters(self, handler, mock_repository, sample_meals):
        """Test combining date range and meal type filters."""
        today = datetime.now(timezone.utc)
        yesterday = today - timedelta(days=1)

        query = GetMealHistoryQuery(
            user_id="user123",
            start_date=yesterday,
            end_date=today,
            meal_type="LUNCH",
            limit=10,
            offset=0,
        )

        mock_repository.get_by_user_and_date_range.return_value = sample_meals

        result = await handler.handle(query)

        # Should filter by meal type after fetching
        assert all(m.meal_type == "LUNCH" for m in result)
