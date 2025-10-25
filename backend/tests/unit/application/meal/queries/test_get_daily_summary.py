"""Unit tests for GetDailySummaryQuery and handler."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime, timezone

from application.meal.queries.get_daily_summary import (
    GetDailySummaryQuery,
    GetDailySummaryQueryHandler,
    DailySummary,
)
from domain.meal.core.entities.meal import Meal


@pytest.fixture
def mock_repository():
    return AsyncMock()


@pytest.fixture
def handler(mock_repository):
    return GetDailySummaryQueryHandler(repository=mock_repository)


@pytest.fixture
def sample_daily_meals():
    """Create sample meals for a day."""
    meals = []

    # Breakfast
    breakfast = MagicMock(spec=Meal)
    breakfast.id = uuid4()
    breakfast.user_id = "user123"
    breakfast.meal_type = "BREAKFAST"
    breakfast.total_calories = 400.0
    breakfast.total_protein = 15.0
    breakfast.total_carbs = 50.0
    breakfast.total_fat = 12.0
    breakfast.total_fiber = 5.0
    meals.append(breakfast)

    # Lunch
    lunch = MagicMock(spec=Meal)
    lunch.id = uuid4()
    lunch.user_id = "user123"
    lunch.meal_type = "LUNCH"
    lunch.total_calories = 600.0
    lunch.total_protein = 30.0
    lunch.total_carbs = 60.0
    lunch.total_fat = 20.0
    lunch.total_fiber = 10.0
    meals.append(lunch)

    # Dinner
    dinner = MagicMock(spec=Meal)
    dinner.id = uuid4()
    dinner.user_id = "user123"
    dinner.meal_type = "DINNER"
    dinner.total_calories = 550.0
    dinner.total_protein = 35.0
    dinner.total_carbs = 45.0
    dinner.total_fat = 22.0
    dinner.total_fiber = 8.0
    meals.append(dinner)

    # Snack
    snack = MagicMock(spec=Meal)
    snack.id = uuid4()
    snack.user_id = "user123"
    snack.meal_type = "SNACK"
    snack.total_calories = 150.0
    snack.total_protein = 5.0
    snack.total_carbs = 20.0
    snack.total_fat = 6.0
    snack.total_fiber = 2.0
    meals.append(snack)

    return meals


class TestGetDailySummaryQueryHandler:
    """Test GetDailySummaryQueryHandler."""

    @pytest.mark.asyncio
    async def test_get_daily_summary_success(self, handler, mock_repository, sample_daily_meals):
        """Test successful daily summary calculation."""
        today = datetime.now(timezone.utc)
        query = GetDailySummaryQuery(user_id="user123", date=today)

        mock_repository.get_by_user_and_date_range.return_value = sample_daily_meals

        result = await handler.handle(query)

        assert isinstance(result, DailySummary)
        assert result.total_calories == 1700.0  # 400 + 600 + 550 + 150
        assert result.total_protein == 85.0  # 15 + 30 + 35 + 5
        assert result.total_carbs == 175.0  # 50 + 60 + 45 + 20
        assert result.total_fat == 60.0  # 12 + 20 + 22 + 6
        assert result.total_fiber == 25.0  # 5 + 10 + 8 + 2
        assert result.meal_count == 4

    @pytest.mark.asyncio
    async def test_get_daily_summary_breakdown_by_type(
        self, handler, mock_repository, sample_daily_meals
    ):
        """Test breakdown by meal type."""
        today = datetime.now(timezone.utc)
        query = GetDailySummaryQuery(user_id="user123", date=today)

        mock_repository.get_by_user_and_date_range.return_value = sample_daily_meals

        result = await handler.handle(query)

        assert result.breakdown_by_type["BREAKFAST"] == 400.0
        assert result.breakdown_by_type["LUNCH"] == 600.0
        assert result.breakdown_by_type["DINNER"] == 550.0
        assert result.breakdown_by_type["SNACK"] == 150.0

    @pytest.mark.asyncio
    async def test_get_daily_summary_no_meals(self, handler, mock_repository):
        """Test daily summary with no meals."""
        today = datetime.now(timezone.utc)
        query = GetDailySummaryQuery(user_id="user123", date=today)

        mock_repository.get_by_user_and_date_range.return_value = []

        result = await handler.handle(query)

        assert result.total_calories == 0.0
        assert result.total_protein == 0.0
        assert result.total_carbs == 0.0
        assert result.total_fat == 0.0
        assert result.total_fiber == 0.0
        assert result.meal_count == 0
        assert result.breakdown_by_type["BREAKFAST"] == 0.0

    @pytest.mark.asyncio
    async def test_get_daily_summary_default_date(
        self, handler, mock_repository, sample_daily_meals
    ):
        """Test daily summary with default date (today)."""
        # Query without date should default to today
        query = GetDailySummaryQuery(user_id="user123")

        mock_repository.get_by_user_and_date_range.return_value = sample_daily_meals

        result = await handler.handle(query)

        # Should return summary for today
        assert isinstance(result, DailySummary)
        assert result.total_calories == 1700.0

    @pytest.mark.asyncio
    async def test_get_daily_summary_date_range_called_correctly(
        self, handler, mock_repository, sample_daily_meals
    ):
        """Test that date range is calculated correctly."""
        date = datetime(2025, 10, 24, 15, 30, 0, tzinfo=timezone.utc)
        query = GetDailySummaryQuery(user_id="user123", date=date)

        mock_repository.get_by_user_and_date_range.return_value = sample_daily_meals

        await handler.handle(query)

        # Verify repository was called with start/end of day
        call_args = mock_repository.get_by_user_and_date_range.call_args
        assert call_args.kwargs["user_id"] == "user123"

        # Start should be 00:00:00
        start_date = call_args.kwargs["start_date"]
        assert start_date.hour == 0
        assert start_date.minute == 0
        assert start_date.second == 0

        # End should be 23:59:59
        end_date = call_args.kwargs["end_date"]
        assert end_date.hour == 23
        assert end_date.minute == 59
        assert end_date.second == 59
