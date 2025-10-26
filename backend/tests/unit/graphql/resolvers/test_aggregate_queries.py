"""Unit tests for aggregate query resolvers.

Tests the 4 aggregate queries for meal data operations:
- meal: Single meal by ID with authorization
- mealHistory: Meal list with filters (date range, meal type) + pagination
- searchMeals: Full-text search in entries and notes
- dailySummary: Daily nutrition aggregation with breakdown by meal type
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import Any
from datetime import datetime, timezone
from uuid import uuid4

from graphql.resolvers.meal.aggregate_queries import AggregateQueries
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


@pytest.fixture
def aggregate_queries() -> AggregateQueries:
    """Create AggregateQueries resolver instance."""
    return AggregateQueries()


@pytest.fixture
def sample_meal() -> DomainMeal:
    """Create sample domain meal for testing."""
    meal_id = MealId.generate()

    entry = DomainMealEntry(
        id=uuid4(),
        meal_id=meal_id.value,
        name="chicken_breast",
        display_name="Chicken Breast",
        quantity_g=150.0,
        calories=165,
        protein=31.0,
        carbs=0.0,
        fat=3.6,
        fiber=0.0,
        sugar=0.0,
        sodium=74.0,
        confidence=0.95,
    )

    meal = DomainMeal(
        id=meal_id.value,
        user_id="user123",
        timestamp=datetime(2025, 10, 25, 12, 30, 0, tzinfo=timezone.utc),
        meal_type="LUNCH",
        entries=[entry],
        notes="Grilled chicken with vegetables",
        total_calories=165,
        total_protein=31.0,
        total_carbs=0.0,
        total_fat=3.6,
        total_fiber=0.0,
        total_sugar=0.0,
        total_sodium=74.0,
    )

    return meal


# ============================================
# meal Query Tests
# ============================================


@pytest.mark.asyncio
async def test_meal_success(
    aggregate_queries: AggregateQueries, mock_info: Any, sample_meal: DomainMeal
) -> None:
    """Test meal query with valid ID."""
    # Arrange
    meal_id = str(sample_meal.id)
    user_id = "user123"

    repository = mock_info.context.get("meal_repository")
    repository.get_by_id.return_value = sample_meal

    # Act
    result = await aggregate_queries.meal(  # type: ignore[misc,call-arg]
        info=mock_info,
        meal_id=meal_id,
        user_id=user_id,
    )

    # Assert
    assert result is not None
    assert result.id == meal_id
    assert result.user_id == user_id
    assert result.meal_type.value == "LUNCH"
    assert len(result.entries) == 1
    assert result.entries[0].name == "chicken_breast"
    assert result.entries[0].display_name == "Chicken Breast"
    assert result.total_calories == 165
    assert result.total_protein == 31.0
    assert result.notes == "Grilled chicken with vegetables"


@pytest.mark.asyncio
async def test_meal_not_found(aggregate_queries: AggregateQueries, mock_info: Any) -> None:
    """Test meal query when meal not found."""
    # Arrange
    repository = mock_info.context.get("meal_repository")
    repository.get_by_id.return_value = None

    # Act
    result = await aggregate_queries.meal(  # type: ignore[misc,call-arg]
        info=mock_info,
        meal_id=str(uuid4()),
        user_id="user123",
    )

    # Assert
    assert result is None


@pytest.mark.asyncio
async def test_meal_repository_not_available(aggregate_queries: AggregateQueries) -> None:
    """Test meal query when repository not available."""
    # Arrange
    mock_info = MagicMock()
    mock_info.context.get.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match="MealRepository not available in context"):
        await aggregate_queries.meal(  # type: ignore[misc,call-arg]
            info=mock_info,
            meal_id=str(uuid4()),
            user_id="user123",
        )


# ============================================
# mealHistory Query Tests
# ============================================


@pytest.mark.asyncio
async def test_meal_history_success(
    aggregate_queries: AggregateQueries, mock_info: Any, sample_meal: DomainMeal
) -> None:
    """Test mealHistory query with basic filters."""
    # Arrange
    repository = mock_info.context.get("meal_repository")
    repository.get_by_user.return_value = [sample_meal]
    repository.count_by_user.return_value = 1  # Mock total count

    # Act
    result = await aggregate_queries.meal_history(  # type: ignore[misc,call-arg]
        info=mock_info,
        user_id="user123",
        limit=20,
        offset=0,
    )

    # Assert
    assert result.meals is not None
    assert len(result.meals) == 1
    assert result.meals[0].id == str(sample_meal.id)
    assert result.total_count == 1
    assert result.has_more is False


@pytest.mark.asyncio
async def test_meal_history_with_date_range(
    aggregate_queries: AggregateQueries, mock_info: Any, sample_meal: DomainMeal
) -> None:
    """Test mealHistory query with date range filter."""
    # Arrange
    start_date = datetime(2025, 10, 25, 0, 0, 0, tzinfo=timezone.utc)
    end_date = datetime(2025, 10, 25, 23, 59, 59, tzinfo=timezone.utc)

    repository = mock_info.context.get("meal_repository")
    repository.get_by_user_and_date_range.return_value = [sample_meal]

    # Act
    result = await aggregate_queries.meal_history(  # type: ignore[misc,call-arg]
        info=mock_info,
        user_id="user123",
        start_date=start_date,
        end_date=end_date,
        limit=20,
        offset=0,
    )

    # Assert
    assert len(result.meals) == 1
    # Note: Resolver calls repository twice for date range queries
    # 1st call: Fetch paginated results
    # 2nd call: Calculate total count
    assert repository.get_by_user_and_date_range.call_count == 2


@pytest.mark.asyncio
async def test_meal_history_pagination(aggregate_queries: AggregateQueries, mock_info: Any) -> None:
    """Test mealHistory query with pagination (has_more flag)."""
    # Arrange
    meals = []
    for i in range(20):
        meal_id = MealId.generate()
        meal = DomainMeal(
            id=meal_id.value,
            user_id="user123",
            timestamp=datetime(2025, 10, 25, i, 0, 0, tzinfo=timezone.utc),
            meal_type="LUNCH",
            entries=[
                DomainMealEntry(
                    id=uuid4(),
                    meal_id=meal_id.value,
                    name="food",
                    display_name="Food",
                    quantity_g=100.0,
                    calories=100,
                    protein=5.0,
                    carbs=10.0,
                    fat=3.0,
                    fiber=1.0,
                    sugar=1.0,
                    sodium=5.0,
                )
            ],
            total_calories=100,
            total_protein=5.0,
            total_carbs=10.0,
            total_fat=3.0,
            total_fiber=1.0,
            total_sugar=1.0,
            total_sodium=5.0,
        )
        meals.append(meal)

    repository = mock_info.context.get("meal_repository")
    repository.get_by_user.return_value = meals
    repository.count_by_user.return_value = 20  # Mock total count

    # Act
    result = await aggregate_queries.meal_history(  # type: ignore[misc,call-arg]
        info=mock_info,
        user_id="user123",
        limit=20,
        offset=0,
    )

    # Assert
    assert len(result.meals) == 20
    assert result.total_count == 20
    assert result.has_more is False  # No more when offset + len == total


@pytest.mark.asyncio
async def test_meal_history_empty(aggregate_queries: AggregateQueries, mock_info: Any) -> None:
    """Test mealHistory query with no results."""
    # Arrange
    repository = mock_info.context.get("meal_repository")
    repository.get_by_user.return_value = []
    repository.count_by_user.return_value = 0  # Mock total count

    # Act
    result = await aggregate_queries.meal_history(  # type: ignore[misc,call-arg]
        info=mock_info,
        user_id="user123",
        limit=20,
        offset=0,
    )

    # Assert
    assert len(result.meals) == 0
    assert result.total_count == 0
    assert result.has_more is False


# ============================================
# searchMeals Query Tests
# ============================================


@pytest.mark.asyncio
async def test_search_meals_by_entry_name(
    aggregate_queries: AggregateQueries, mock_info: Any, sample_meal: DomainMeal
) -> None:
    """Test searchMeals query matching entry name."""
    # Arrange
    repository = mock_info.context.get("meal_repository")
    repository.get_by_user.return_value = [sample_meal]

    # Act
    result = await aggregate_queries.search_meals(  # type: ignore[misc,call-arg]
        info=mock_info,
        user_id="user123",
        query_text="chicken",
        limit=20,
        offset=0,
    )

    # Assert
    assert len(result.meals) == 1
    assert result.meals[0].id == str(sample_meal.id)
    assert result.total_count == 1


@pytest.mark.asyncio
async def test_search_meals_by_notes(
    aggregate_queries: AggregateQueries, mock_info: Any, sample_meal: DomainMeal
) -> None:
    """Test searchMeals query matching notes."""
    # Arrange
    repository = mock_info.context.get("meal_repository")
    repository.get_by_user.return_value = [sample_meal]

    # Act
    result = await aggregate_queries.search_meals(  # type: ignore[misc,call-arg]
        info=mock_info,
        user_id="user123",
        query_text="grilled",
        limit=20,
        offset=0,
    )

    # Assert
    assert len(result.meals) == 1


@pytest.mark.asyncio
async def test_search_meals_case_insensitive(
    aggregate_queries: AggregateQueries, mock_info: Any, sample_meal: DomainMeal
) -> None:
    """Test searchMeals query is case-insensitive."""
    # Arrange
    repository = mock_info.context.get("meal_repository")
    repository.get_by_user.return_value = [sample_meal]

    # Act
    result = await aggregate_queries.search_meals(  # type: ignore[misc,call-arg]
        info=mock_info,
        user_id="user123",
        query_text="CHICKEN",
        limit=20,
        offset=0,
    )

    # Assert
    assert len(result.meals) == 1


@pytest.mark.asyncio
async def test_search_meals_no_match(
    aggregate_queries: AggregateQueries, mock_info: Any, sample_meal: DomainMeal
) -> None:
    """Test searchMeals query with no matching results."""
    # Arrange
    repository = mock_info.context.get("meal_repository")
    repository.get_by_user.return_value = [sample_meal]

    # Act
    result = await aggregate_queries.search_meals(  # type: ignore[misc,call-arg]
        info=mock_info,
        user_id="user123",
        query_text="pizza",
        limit=20,
        offset=0,
    )

    # Assert
    assert len(result.meals) == 0
    assert result.total_count == 0


# ============================================
# dailySummary Query Tests
# ============================================


@pytest.mark.asyncio
async def test_daily_summary_success(aggregate_queries: AggregateQueries, mock_info: Any) -> None:
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
    result = await aggregate_queries.daily_summary(  # type: ignore[misc,call-arg]
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
async def test_daily_summary_empty_day(aggregate_queries: AggregateQueries, mock_info: Any) -> None:
    """Test dailySummary query for day with no meals."""
    # Arrange
    repository = mock_info.context.get("meal_repository")
    repository.get_by_user_and_date_range.return_value = []

    # Act
    result = await aggregate_queries.daily_summary(  # type: ignore[misc,call-arg]
        info=mock_info,
        user_id="user123",
        date=datetime(2025, 10, 25, tzinfo=timezone.utc),
    )

    # Assert
    assert result.total_calories == 0.0
    assert result.total_protein == 0.0
    assert result.total_carbs == 0.0
    assert result.total_fat == 0.0
    assert result.meal_count == 0


@pytest.mark.asyncio
async def test_daily_summary_single_meal_type(
    aggregate_queries: AggregateQueries, mock_info: Any
) -> None:
    """Test dailySummary query with meals of same type."""
    # Arrange
    snack1_id = MealId.generate()
    snack1 = DomainMeal(
        id=snack1_id.value,
        user_id="user123",
        timestamp=datetime(2025, 10, 25, 10, 0, 0, tzinfo=timezone.utc),
        meal_type="SNACK",
        entries=[
            DomainMealEntry(
                id=uuid4(),
                meal_id=snack1_id.value,
                name="apple",
                display_name="Apple",
                quantity_g=100.0,
                calories=52,
                protein=0.3,
                carbs=14.0,
                fat=0.2,
                fiber=2.4,
                sugar=10.0,
                sodium=1.0,
            )
        ],
        total_calories=52,
        total_protein=0.3,
        total_carbs=14.0,
        total_fat=0.2,
        total_fiber=2.4,
        total_sugar=10.0,
        total_sodium=1.0,
    )

    snack2_id = MealId.generate()
    snack2 = DomainMeal(
        id=snack2_id.value,
        user_id="user123",
        timestamp=datetime(2025, 10, 25, 15, 0, 0, tzinfo=timezone.utc),
        meal_type="SNACK",
        entries=[
            DomainMealEntry(
                id=uuid4(),
                meal_id=snack2_id.value,
                name="almonds",
                display_name="Almonds",
                quantity_g=30.0,
                calories=173,
                protein=6.0,
                carbs=6.0,
                fat=15.0,
                fiber=3.5,
                sugar=1.0,
                sodium=0.0,
            )
        ],
        total_calories=173,
        total_protein=6.0,
        total_carbs=6.0,
        total_fat=15.0,
        total_fiber=3.5,
        total_sugar=1.0,
        total_sodium=0.0,
    )

    repository = mock_info.context.get("meal_repository")
    repository.get_by_user_and_date_range.return_value = [snack1, snack2]

    # Act
    result = await aggregate_queries.daily_summary(  # type: ignore[misc,call-arg]
        info=mock_info,
        user_id="user123",
        date=datetime(2025, 10, 25, tzinfo=timezone.utc),
    )

    # Assert
    assert result.total_calories == 225.0  # 52 + 173
    assert result.meal_count == 2

    import json

    breakdown = json.loads(result.breakdown_by_type)
    assert breakdown["SNACK"] == 225.0
    # Other meal types should be 0
    assert breakdown.get("BREAKFAST", 0) == 0.0
    assert breakdown.get("LUNCH", 0) == 0.0
    assert breakdown.get("DINNER", 0) == 0.0
