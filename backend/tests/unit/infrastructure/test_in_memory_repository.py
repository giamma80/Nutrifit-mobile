"""Unit tests for InMemoryMealRepository.

Tests focus on:
- Repository initialization
- Save and retrieve operations
- Query methods (get_by_user, get_by_user_and_date_range)
- Delete operations
- Authorization checks (user_id filtering)
- Pagination
- Edge cases

Note: These are UNIT tests for in-memory implementation.
For integration tests with real database, see tests/integration/infrastructure/
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from infrastructure.persistence.in_memory.meal_repository import (
    InMemoryMealRepository,
)
from domain.meal.core.entities.meal import Meal
from domain.meal.core.entities.meal_entry import MealEntry


@pytest.fixture
def repository() -> InMemoryMealRepository:
    """Fixture providing clean InMemoryMealRepository."""
    return InMemoryMealRepository()


@pytest.fixture
def sample_meal() -> Meal:
    """Fixture providing sample meal."""
    now = datetime.now(timezone.utc)
    meal_id = uuid4()

    entry = MealEntry(
        id=uuid4(),
        meal_id=meal_id,
        name="chicken_breast",
        display_name="Petto di pollo",
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

    meal = Meal(
        id=meal_id,
        user_id="user123",
        timestamp=now,
        meal_type="LUNCH",
        entries=[entry],
    )
    meal._recalculate_totals()
    return meal


class TestRepositoryInit:
    """Test repository initialization."""

    def test_init(self) -> None:
        """Test repository initializes with empty storage."""
        repository = InMemoryMealRepository()
        assert repository._storage == {}


class TestSave:
    """Test save method."""

    @pytest.mark.asyncio
    async def test_save_new_meal(
        self, repository: InMemoryMealRepository, sample_meal: Meal
    ) -> None:
        """Test saving a new meal."""
        await repository.save(sample_meal)

        # Verify meal is in storage
        assert sample_meal.id in repository._storage
        stored = repository._storage[sample_meal.id]
        assert stored.user_id == "user123"
        assert stored.meal_type == "LUNCH"

    @pytest.mark.asyncio
    async def test_save_updates_existing_meal(
        self, repository: InMemoryMealRepository, sample_meal: Meal
    ) -> None:
        """Test saving updates an existing meal."""
        await repository.save(sample_meal)

        # Modify meal
        original_updated_at = sample_meal.updated_at
        sample_meal.notes = "Updated notes"

        # Save again
        await repository.save(sample_meal)

        # Verify meal was updated
        stored = repository._storage[sample_meal.id]
        assert stored.notes == "Updated notes"
        assert stored.updated_at > original_updated_at

    @pytest.mark.asyncio
    async def test_save_creates_deep_copy(
        self, repository: InMemoryMealRepository, sample_meal: Meal
    ) -> None:
        """Test save creates deep copy to prevent external modifications."""
        await repository.save(sample_meal)

        # Modify original meal after save
        sample_meal.notes = "External modification"

        # Stored meal should not be affected
        stored = repository._storage[sample_meal.id]
        assert stored.notes != "External modification"


class TestGetById:
    """Test get_by_id method."""

    @pytest.mark.asyncio
    async def test_get_by_id_success(
        self, repository: InMemoryMealRepository, sample_meal: Meal
    ) -> None:
        """Test retrieving meal by ID."""
        await repository.save(sample_meal)

        retrieved = await repository.get_by_id(sample_meal.id, "user123")

        assert retrieved is not None
        assert retrieved.id == sample_meal.id
        assert retrieved.user_id == "user123"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(
        self, repository: InMemoryMealRepository
    ) -> None:
        """Test retrieving non-existent meal."""
        retrieved = await repository.get_by_id(uuid4(), "user123")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_get_by_id_wrong_user(
        self, repository: InMemoryMealRepository, sample_meal: Meal
    ) -> None:
        """Test retrieving meal with wrong user_id (authorization)."""
        await repository.save(sample_meal)

        # Try to retrieve with different user_id
        retrieved = await repository.get_by_id(sample_meal.id, "user456")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_get_by_id_returns_deep_copy(
        self, repository: InMemoryMealRepository, sample_meal: Meal
    ) -> None:
        """Test get_by_id returns deep copy."""
        await repository.save(sample_meal)

        retrieved = await repository.get_by_id(sample_meal.id, "user123")
        assert retrieved is not None

        # Modify retrieved meal
        retrieved.notes = "External modification"

        # Stored meal should not be affected
        stored = repository._storage[sample_meal.id]
        assert stored.notes != "External modification"


class TestGetByUser:
    """Test get_by_user method."""

    @pytest.mark.asyncio
    async def test_get_by_user_empty(
        self, repository: InMemoryMealRepository
    ) -> None:
        """Test get_by_user with no meals."""
        meals = await repository.get_by_user("user123")
        assert meals == []

    @pytest.mark.asyncio
    async def test_get_by_user_single_meal(
        self, repository: InMemoryMealRepository, sample_meal: Meal
    ) -> None:
        """Test get_by_user with single meal."""
        await repository.save(sample_meal)

        meals = await repository.get_by_user("user123")

        assert len(meals) == 1
        assert meals[0].id == sample_meal.id

    @pytest.mark.asyncio
    async def test_get_by_user_multiple_meals(
        self, repository: InMemoryMealRepository
    ) -> None:
        """Test get_by_user with multiple meals."""
        now = datetime.now(timezone.utc)

        # Create 3 meals with different timestamps
        for i in range(3):
            meal = Meal(
                id=uuid4(),
                user_id="user123",
                timestamp=now - timedelta(hours=i),
                meal_type="LUNCH",
                entries=[],
            )
            await repository.save(meal)

        meals = await repository.get_by_user("user123")

        assert len(meals) == 3
        # Should be ordered by timestamp descending (newest first)
        assert meals[0].timestamp > meals[1].timestamp > meals[2].timestamp

    @pytest.mark.asyncio
    async def test_get_by_user_filters_by_user_id(
        self, repository: InMemoryMealRepository, sample_meal: Meal
    ) -> None:
        """Test get_by_user filters by user_id."""
        await repository.save(sample_meal)

        # Create meal for different user
        other_meal = Meal(
            id=uuid4(),
            user_id="user456",
            timestamp=datetime.now(timezone.utc),
            meal_type="DINNER",
            entries=[],
        )
        await repository.save(other_meal)

        # Get meals for user123
        meals = await repository.get_by_user("user123")

        assert len(meals) == 1
        assert meals[0].user_id == "user123"

    @pytest.mark.asyncio
    async def test_get_by_user_pagination(
        self, repository: InMemoryMealRepository
    ) -> None:
        """Test get_by_user pagination."""
        now = datetime.now(timezone.utc)

        # Create 5 meals
        for i in range(5):
            meal = Meal(
                id=uuid4(),
                user_id="user123",
                timestamp=now - timedelta(hours=i),
                meal_type="LUNCH",
                entries=[],
            )
            await repository.save(meal)

        # Get first 3 meals
        page1 = await repository.get_by_user("user123", limit=3, offset=0)
        assert len(page1) == 3

        # Get next 2 meals
        page2 = await repository.get_by_user("user123", limit=3, offset=3)
        assert len(page2) == 2

        # Verify no overlap
        page1_ids = {m.id for m in page1}
        page2_ids = {m.id for m in page2}
        assert page1_ids.isdisjoint(page2_ids)


class TestGetByUserAndDateRange:
    """Test get_by_user_and_date_range method."""

    @pytest.mark.asyncio
    async def test_get_by_user_and_date_range_empty(
        self, repository: InMemoryMealRepository
    ) -> None:
        """Test date range query with no meals."""
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)

        meals = await repository.get_by_user_and_date_range(
            "user123", yesterday, now
        )
        assert meals == []

    @pytest.mark.asyncio
    async def test_get_by_user_and_date_range_filters(
        self, repository: InMemoryMealRepository
    ) -> None:
        """Test date range filtering."""
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)
        two_days_ago = now - timedelta(days=2)

        # Create meals at different times
        meal_in_range = Meal(
            id=uuid4(),
            user_id="user123",
            timestamp=yesterday,
            meal_type="LUNCH",
            entries=[],
        )
        meal_out_of_range = Meal(
            id=uuid4(),
            user_id="user123",
            timestamp=two_days_ago,
            meal_type="BREAKFAST",
            entries=[],
        )

        await repository.save(meal_in_range)
        await repository.save(meal_out_of_range)

        # Query range: yesterday to now
        meals = await repository.get_by_user_and_date_range(
            "user123", yesterday, now
        )

        assert len(meals) == 1
        assert meals[0].id == meal_in_range.id

    @pytest.mark.asyncio
    async def test_get_by_user_and_date_range_ordering(
        self, repository: InMemoryMealRepository
    ) -> None:
        """Test date range results are ordered ascending."""
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)

        # Create 3 meals
        for i in range(3):
            meal = Meal(
                id=uuid4(),
                user_id="user123",
                timestamp=yesterday + timedelta(hours=i),
                meal_type="LUNCH",
                entries=[],
            )
            await repository.save(meal)

        meals = await repository.get_by_user_and_date_range(
            "user123", yesterday, now
        )

        assert len(meals) == 3
        # Should be ordered by timestamp ascending (oldest first)
        assert meals[0].timestamp < meals[1].timestamp < meals[2].timestamp


class TestDelete:
    """Test delete method."""

    @pytest.mark.asyncio
    async def test_delete_success(
        self, repository: InMemoryMealRepository, sample_meal: Meal
    ) -> None:
        """Test deleting a meal."""
        await repository.save(sample_meal)

        result = await repository.delete(sample_meal.id, "user123")

        assert result is True
        assert sample_meal.id not in repository._storage

    @pytest.mark.asyncio
    async def test_delete_not_found(
        self, repository: InMemoryMealRepository
    ) -> None:
        """Test deleting non-existent meal."""
        result = await repository.delete(uuid4(), "user123")
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_wrong_user(
        self, repository: InMemoryMealRepository, sample_meal: Meal
    ) -> None:
        """Test deleting meal with wrong user_id (authorization)."""
        await repository.save(sample_meal)

        result = await repository.delete(sample_meal.id, "user456")

        assert result is False
        # Meal should still be in storage
        assert sample_meal.id in repository._storage


class TestExists:
    """Test exists method."""

    @pytest.mark.asyncio
    async def test_exists_true(
        self, repository: InMemoryMealRepository, sample_meal: Meal
    ) -> None:
        """Test exists returns True for existing meal."""
        await repository.save(sample_meal)

        result = await repository.exists(sample_meal.id, "user123")
        assert result is True

    @pytest.mark.asyncio
    async def test_exists_false_not_found(
        self, repository: InMemoryMealRepository
    ) -> None:
        """Test exists returns False for non-existent meal."""
        result = await repository.exists(uuid4(), "user123")
        assert result is False

    @pytest.mark.asyncio
    async def test_exists_false_wrong_user(
        self, repository: InMemoryMealRepository, sample_meal: Meal
    ) -> None:
        """Test exists returns False for wrong user."""
        await repository.save(sample_meal)

        result = await repository.exists(sample_meal.id, "user456")
        assert result is False


class TestCountByUser:
    """Test count_by_user method."""

    @pytest.mark.asyncio
    async def test_count_by_user_empty(
        self, repository: InMemoryMealRepository
    ) -> None:
        """Test count with no meals."""
        count = await repository.count_by_user("user123")
        assert count == 0

    @pytest.mark.asyncio
    async def test_count_by_user_single(
        self, repository: InMemoryMealRepository, sample_meal: Meal
    ) -> None:
        """Test count with single meal."""
        await repository.save(sample_meal)

        count = await repository.count_by_user("user123")
        assert count == 1

    @pytest.mark.asyncio
    async def test_count_by_user_multiple(
        self, repository: InMemoryMealRepository
    ) -> None:
        """Test count with multiple meals."""
        now = datetime.now(timezone.utc)

        # Create 5 meals for user123
        for i in range(5):
            meal = Meal(
                id=uuid4(),
                user_id="user123",
                timestamp=now - timedelta(hours=i),
                meal_type="LUNCH",
                entries=[],
            )
            await repository.save(meal)

        # Create 2 meals for user456
        for i in range(2):
            meal = Meal(
                id=uuid4(),
                user_id="user456",
                timestamp=now - timedelta(hours=i),
                meal_type="LUNCH",
                entries=[],
            )
            await repository.save(meal)

        count_user123 = await repository.count_by_user("user123")
        count_user456 = await repository.count_by_user("user456")

        assert count_user123 == 5
        assert count_user456 == 2


class TestClear:
    """Test clear utility method."""

    @pytest.mark.asyncio
    async def test_clear(
        self, repository: InMemoryMealRepository, sample_meal: Meal
    ) -> None:
        """Test clear removes all meals."""
        await repository.save(sample_meal)
        assert len(repository._storage) == 1

        repository.clear()
        assert len(repository._storage) == 0
