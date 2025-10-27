"""Unit tests for global query resolvers.

Tests global queries that span multiple domains:
- dailySummary: Daily nutrition and activity aggregation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import Any
from datetime import datetime, timezone
from uuid import uuid4

from graphql.resolvers.global_queries import resolve_daily_summary
from domain.meal.core.entities.meal import Meal as DomainMeal
from domain.meal.core.entities.meal_entry import MealEntry as DomainMealEntry
from domain.meal.core.value_objects.meal_id import MealId


@pytest.fixture
def mock_context() -> Any:
    """Create mock Strawberry context with meal repository."""
    mocks = {
        "meal_repository": AsyncMock(),
    }

    context = MagicMock()
    context.get = MagicMock(side_effect=lambda key: mocks.get(key))
    return context


@pytest.fixture
def mock_info(mock_context: Any) -> Any:
    """Create mock Strawberry Info object."""
    info = MagicMock()
    info.context = mock_context
    return info


# ============================================
# dailySummary Query Tests
# ============================================


@pytest.mark.asyncio
async def test_daily_summary_success(mock_info: Any) -> None:
    """Test dailySummary query with multiple meals."""
    # Arrange
    breakfast_id = MealId.generate()
    breakfast = DomainMeal(
        id=breakfast_id.value,
        user_id="user123",
        timestamp=datetime(2025, 10, 25, 8, 0, 0, tzinfo=timezone.utc),
        meal_type="BREAKFAST",
        entries=[
            DomainMealEntry(
                id=uuid4(),
                meal_id=breakfast_id.value,
                name="oatmeal",
                display_name="Oatmeal",
                quantity_g=100.0,
                calories=150,
                protein=5.0,
                carbs=27.0,
                fat=3.0,
                fiber=4.0,
                sugar=1.0,
                sodium=5.0,
            )
        ],
        total_calories=150,
        total_protein=5.0,
        total_carbs=27.0,
        total_fat=3.0,
        total_fiber=4.0,
        total_sugar=1.0,
        total_sodium=5.0,
    )

    lunch_id = MealId.generate()
    lunch = DomainMeal(
        id=lunch_id.value,
        user_id="user123",
        timestamp=datetime(2025, 10, 25, 12, 30, 0, tzinfo=timezone.utc),
        meal_type="LUNCH",
        entries=[
            DomainMealEntry(
                id=uuid4(),
                meal_id=lunch_id.value,
                name="chicken",
                display_name="Chicken",
                quantity_g=150.0,
                calories=250,
                protein=40.0,
                carbs=0.0,
                fat=8.0,
                fiber=0.0,
                sugar=0.0,
                sodium=100.0,
            )
        ],
        total_calories=250,
        total_protein=40.0,
        total_carbs=0.0,
        total_fat=8.0,
        total_fiber=0.0,
        total_sugar=0.0,
        total_sodium=100.0,
    )

    repository = mock_info.context.get("meal_repository")
    repository.get_by_user_and_date_range.return_value = [breakfast, lunch]

    # Act
    result = await resolve_daily_summary(
        info=mock_info,
        user_id="user123",
        date=datetime(2025, 10, 25, tzinfo=timezone.utc),
    )

    # Assert
    assert result.total_calories == 400.0  # 150 + 250
    assert result.total_protein == 45.0  # 5 + 40
    assert result.total_carbs == 27.0
    assert result.total_fat == 11.0
    assert result.total_fiber == 4.0
    assert result.meal_count == 2

    # Check breakdown
    import json

    breakdown = json.loads(result.breakdown_by_type)
    assert "BREAKFAST" in breakdown
    assert "LUNCH" in breakdown
    assert breakdown["BREAKFAST"] == 150
    assert breakdown["LUNCH"] == 250


@pytest.mark.asyncio
async def test_daily_summary_empty_day(mock_info: Any) -> None:
    """Test dailySummary query for day with no meals."""
    # Arrange
    repository = mock_info.context.get("meal_repository")
    repository.get_by_user_and_date_range.return_value = []

    # Act
    result = await resolve_daily_summary(
        info=mock_info,
        user_id="user123",
        date=datetime(2025, 10, 25, tzinfo=timezone.utc),
    )

    # Assert
    assert result.total_calories == 0.0
    assert result.total_protein == 0.0
    assert result.total_carbs == 0.0
    assert result.total_fat == 0.0
    assert result.total_fiber == 0.0
    assert result.meal_count == 0

    # Check breakdown is empty
    import json

    breakdown = json.loads(result.breakdown_by_type)
    # Note: The domain layer returns all meal types with 0.0 values for empty day
    assert all(v == 0.0 for v in breakdown.values())
    assert set(breakdown.keys()) == {"BREAKFAST", "LUNCH", "DINNER", "SNACK"}


@pytest.mark.asyncio
async def test_daily_summary_single_meal_type(mock_info: Any) -> None:
    """Test dailySummary with only one meal type."""
    # Arrange
    meal_id = MealId.generate()
    dinner = DomainMeal(
        id=meal_id.value,
        user_id="user123",
        timestamp=datetime(2025, 10, 25, 19, 0, 0, tzinfo=timezone.utc),
        meal_type="DINNER",
        entries=[
            DomainMealEntry(
                id=uuid4(),
                meal_id=meal_id.value,
                name="pasta",
                display_name="Pasta",
                quantity_g=200.0,
                calories=400,
                protein=12.0,
                carbs=75.0,
                fat=5.0,
                fiber=3.0,
                sugar=2.0,
                sodium=50.0,
            )
        ],
        total_calories=400,
        total_protein=12.0,
        total_carbs=75.0,
        total_fat=5.0,
        total_fiber=3.0,
        total_sugar=2.0,
        total_sodium=50.0,
    )

    repository = mock_info.context.get("meal_repository")
    repository.get_by_user_and_date_range.return_value = [dinner]

    # Act
    result = await resolve_daily_summary(
        info=mock_info,
        user_id="user123",
        date=datetime(2025, 10, 25, tzinfo=timezone.utc),
    )

    # Assert
    assert result.total_calories == 400.0
    assert result.total_protein == 12.0
    assert result.meal_count == 1

    # Check breakdown has only DINNER
    import json

    breakdown = json.loads(result.breakdown_by_type)
    # Note: Domain layer returns all meal types, with 0.0 for unused types
    assert breakdown["DINNER"] == 400
    assert breakdown.get("BREAKFAST", 0) == 0.0
    assert breakdown.get("LUNCH", 0) == 0.0
    assert breakdown.get("SNACK", 0) == 0.0
