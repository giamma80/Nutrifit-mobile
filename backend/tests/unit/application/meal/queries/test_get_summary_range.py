"""Unit tests for GetSummaryRangeQuery and handler."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone, timedelta

from application.meal.queries.get_summary_range import (
    GetSummaryRangeQuery,
    GetSummaryRangeQueryHandler,
    GroupByPeriod,
)
from domain.meal.core.entities.meal import Meal


@pytest.fixture
def mock_repository():
    return AsyncMock()


@pytest.fixture
def handler(mock_repository):
    return GetSummaryRangeQueryHandler(repository=mock_repository)


@pytest.fixture
def sample_meals():
    """Create sample meals over a week."""
    meals = []
    base_date = datetime(2025, 10, 21, 12, 0, 0, tzinfo=timezone.utc)

    for day in range(7):  # 7 days
        timestamp = base_date + timedelta(days=day)

        # Breakfast
        breakfast = MagicMock(spec=Meal)
        breakfast.user_id = "user123"
        breakfast.timestamp = timestamp.replace(hour=8)
        breakfast.meal_type = "BREAKFAST"
        breakfast.total_calories = 300
        breakfast.total_protein = 10
        breakfast.total_carbs = 50
        breakfast.total_fat = 5
        breakfast.total_fiber = 8
        breakfast.total_sugar = 10
        breakfast.total_sodium = 100
        meals.append(breakfast)

        # Lunch
        lunch = MagicMock(spec=Meal)
        lunch.user_id = "user123"
        lunch.timestamp = timestamp.replace(hour=13)
        lunch.meal_type = "LUNCH"
        lunch.total_calories = 450
        lunch.total_protein = 35
        lunch.total_carbs = 30
        lunch.total_fat = 20
        lunch.total_fiber = 10
        lunch.total_sugar = 5
        lunch.total_sodium = 600
        meals.append(lunch)

    return meals


class TestGetSummaryRangeQueryHandler:
    """Test GetSummaryRangeQueryHandler."""

    @pytest.mark.asyncio
    async def test_summary_range_by_day(self, handler, mock_repository, sample_meals):
        """Test getting summary range grouped by day."""
        start_date = datetime(2025, 10, 21, 0, 0, 0)
        end_date = datetime(2025, 10, 27, 23, 59, 59)

        query = GetSummaryRangeQuery(
            user_id="user123",
            start_date=start_date,
            end_date=end_date,
            group_by=GroupByPeriod.DAY,
        )

        # Mock che filtra correttamente per date range
        # Accetta datetime objects come parametri keyword
        def get_meals_for_range(user_id, start_date, end_date):
            # Converti datetimes naive per confronto
            if start_date.tzinfo is None:
                start_dt = start_date.replace(tzinfo=timezone.utc)
            else:
                start_dt = start_date
            if end_date.tzinfo is None:
                end_dt = end_date.replace(tzinfo=timezone.utc)
            else:
                end_dt = end_date

            return [m for m in sample_meals if start_dt <= m.timestamp <= end_dt]

        mock_repository.get_by_user_and_date_range.side_effect = get_meals_for_range

        results = await handler.handle(query)

        # Should return 7 periods (one per day)
        assert len(results) == 7

        # Check first day
        first_day = results[0]
        assert first_day.period == "2025-10-21"
        assert first_day.total_calories == 750  # 300 + 450
        assert first_day.total_protein == 45  # 10 + 35
        assert first_day.meal_count == 2

        # Verify breakdown
        assert first_day.breakdown_by_type["BREAKFAST"] == 300
        assert first_day.breakdown_by_type["LUNCH"] == 450

    @pytest.mark.asyncio
    async def test_summary_range_by_week(self, handler, mock_repository, sample_meals):
        """Test getting summary range grouped by week."""
        # Week starting Monday 20 Oct through Sunday 26 Oct (ISO week 43)
        start_date = datetime(2025, 10, 20, 0, 0, 0)
        end_date = datetime(2025, 10, 26, 23, 59, 59)

        query = GetSummaryRangeQuery(
            user_id="user123",
            start_date=start_date,
            end_date=end_date,
            group_by=GroupByPeriod.WEEK,
        )

        def get_meals_for_range(user_id, start_date, end_date):
            # Converti per confronto timezone-aware
            if start_date.tzinfo is None:
                start_dt = start_date.replace(tzinfo=timezone.utc)
            else:
                start_dt = start_date
            if end_date.tzinfo is None:
                end_dt = end_date.replace(tzinfo=timezone.utc)
            else:
                end_dt = end_date

            return [m for m in sample_meals if start_dt <= m.timestamp <= end_dt]

        mock_repository.get_by_user_and_date_range.side_effect = get_meals_for_range

        results = await handler.handle(query)

        # Should return 1 period (entire week 43)
        assert len(results) == 1

        week_summary = results[0]
        assert week_summary.period == "2025-W43"
        # 6 days (21-26) * 1 meal/day * 750 calories
        assert week_summary.total_calories >= 4500
        assert week_summary.meal_count >= 6

    @pytest.mark.asyncio
    async def test_summary_range_by_month(self, handler, mock_repository, sample_meals):
        """Test getting summary range grouped by month."""
        start_date = datetime(2025, 10, 1, 0, 0, 0)
        end_date = datetime(2025, 10, 31, 23, 59, 59)

        query = GetSummaryRangeQuery(
            user_id="user123",
            start_date=start_date,
            end_date=end_date,
            group_by=GroupByPeriod.MONTH,
        )

        # Mock che filtra per date range
        def get_meals_for_range(user_id, start_date, end_date):
            # Converti per confronto timezone-aware
            if start_date.tzinfo is None:
                start_dt = start_date.replace(tzinfo=timezone.utc)
            else:
                start_dt = start_date
            if end_date.tzinfo is None:
                end_dt = end_date.replace(tzinfo=timezone.utc)
            else:
                end_dt = end_date

            return [m for m in sample_meals if start_dt <= m.timestamp <= end_dt]

        mock_repository.get_by_user_and_date_range.side_effect = get_meals_for_range

        results = await handler.handle(query)

        # Should return 1 period (entire month)
        assert len(results) == 1

        month_summary = results[0]
        assert month_summary.period == "2025-10"
        assert month_summary.total_calories == 5250
        assert month_summary.meal_count == 14

    @pytest.mark.asyncio
    async def test_summary_range_empty_result(self, handler, mock_repository):
        """Test getting summary range with no meals."""
        start_date = datetime(2025, 10, 21, 0, 0, 0)
        end_date = datetime(2025, 10, 27, 23, 59, 59)

        query = GetSummaryRangeQuery(
            user_id="user123",
            start_date=start_date,
            end_date=end_date,
            group_by=GroupByPeriod.DAY,
        )

        # Mock che restituisce sempre lista vuota
        mock_repository.get_by_user_and_date_range.side_effect = lambda *args, **kwargs: []

        results = await handler.handle(query)

        # Should return 7 periods with zero values
        assert len(results) == 7
        for result in results:
            assert result.total_calories == 0
            assert result.meal_count == 0
            assert result.breakdown_by_type == {}

    @pytest.mark.asyncio
    async def test_summary_range_partial_data(self, handler, mock_repository):
        """Test getting summary range with partial data."""
        start_date = datetime(2025, 10, 21, 0, 0, 0)
        end_date = datetime(2025, 10, 27, 23, 59, 59)

        # Only 1 meal on first day
        base_date = datetime(2025, 10, 21, 12, 0, 0, tzinfo=timezone.utc)
        breakfast = MagicMock(spec=Meal)
        breakfast.user_id = "user123"
        breakfast.timestamp = base_date.replace(hour=8)
        breakfast.meal_type = "BREAKFAST"
        breakfast.total_calories = 300
        breakfast.total_protein = 10
        breakfast.total_carbs = 50
        breakfast.total_fat = 5
        breakfast.total_fiber = 8
        breakfast.total_sugar = 10
        breakfast.total_sodium = 100

        query = GetSummaryRangeQuery(
            user_id="user123",
            start_date=start_date,
            end_date=end_date,
            group_by=GroupByPeriod.DAY,
        )

        def get_meals_for_range(user_id, start_date, end_date):
            if start_date.day == 21:
                return [breakfast]
            return []

        mock_repository.get_by_user_and_date_range.side_effect = get_meals_for_range

        results = await handler.handle(query)

        # Should return 7 periods
        assert len(results) == 7

        # First day has data
        assert results[0].total_calories == 300
        assert results[0].meal_count == 1

        # Other days are empty
        for i in range(1, 7):
            assert results[i].total_calories == 0
            assert results[i].meal_count == 0

    @pytest.mark.asyncio
    async def test_summary_range_respects_date_boundaries(
        self, handler, mock_repository, sample_meals
    ):
        """Test that date boundaries are respected."""
        # Query only 3 days
        start_date = datetime(2025, 10, 21, 0, 0, 0)
        end_date = datetime(2025, 10, 23, 23, 59, 59)

        query = GetSummaryRangeQuery(
            user_id="user123",
            start_date=start_date,
            end_date=end_date,
            group_by=GroupByPeriod.DAY,
        )

        # Mock che filtra per date range
        def get_meals_for_range(user_id, start_date, end_date):
            # Converti per confronto timezone-aware
            if start_date.tzinfo is None:
                start_dt = start_date.replace(tzinfo=timezone.utc)
            else:
                start_dt = start_date
            if end_date.tzinfo is None:
                end_dt = end_date.replace(tzinfo=timezone.utc)
            else:
                end_dt = end_date

            return [m for m in sample_meals if start_dt <= m.timestamp <= end_dt]

        mock_repository.get_by_user_and_date_range.side_effect = get_meals_for_range

        results = await handler.handle(query)

        # Should return only 3 periods
        assert len(results) == 3
        assert results[0].period == "2025-10-21"
        assert results[1].period == "2025-10-22"
        assert results[2].period == "2025-10-23"
