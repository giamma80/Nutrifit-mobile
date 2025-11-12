"""Integration tests for MongoMealRepository.

Tests actual MongoDB operations against a test database.
Requires MONGODB_URI to be set in environment.
"""

import os
from datetime import datetime, timezone

import pytest

from domain.meal.core.models.meal_entry import MealEntry
from domain.meal.core.models.meal_component import MealComponent
from infrastructure.persistence.mongodb.meal_repository import (
    MongoMealRepository,
)


pytestmark = pytest.mark.skipif(
    os.getenv("REPOSITORY_BACKEND") != "mongodb",
    reason="MongoDB integration tests require REPOSITORY_BACKEND=mongodb",
)


@pytest.fixture
async def mongo_repo():
    """Create a MongoMealRepository for testing."""
    repo = MongoMealRepository()
    await repo.connect()
    yield repo
    # Cleanup: delete all test meals
    collection = await repo._get_collection()
    await collection.delete_many({"user_id": {"$regex": "^test_user_"}})
    await repo.disconnect()


@pytest.fixture
def sample_meal():
    """Create a sample meal for testing."""
    return MealEntry(
        meal_id="test_meal_001",
        user_id="test_user_001",
        timestamp=datetime(2025, 11, 12, 12, 0, 0, tzinfo=timezone.utc),
        components=[
            MealComponent(
                component_id="comp_001",
                product_name="Apple",
                quantity_g=150.0,
                calories=78.0,
                protein_g=0.4,
                carbs_g=21.0,
                fat_g=0.3,
            )
        ],
    )


@pytest.mark.asyncio
class TestMongoMealRepositorySave:
    """Test save operations."""

    async def test_save_new_meal(self, mongo_repo, sample_meal):
        """Should successfully save a new meal to MongoDB."""
        await mongo_repo.save(sample_meal)

        # Verify saved
        retrieved = await mongo_repo.get_by_id(
            sample_meal.meal_id, sample_meal.user_id
        )
        assert retrieved is not None
        assert retrieved.meal_id == sample_meal.meal_id
        assert retrieved.user_id == sample_meal.user_id
        assert len(retrieved.components) == 1

    async def test_save_updates_existing_meal(self, mongo_repo, sample_meal):
        """Should update meal if already exists."""
        # Save initial
        await mongo_repo.save(sample_meal)

        # Modify and save again
        sample_meal.components.append(
            MealComponent(
                component_id="comp_002",
                product_name="Banana",
                quantity_g=120.0,
                calories=105.0,
                protein_g=1.3,
                carbs_g=27.0,
                fat_g=0.4,
            )
        )
        await mongo_repo.save(sample_meal)

        # Verify updated
        retrieved = await mongo_repo.get_by_id(
            sample_meal.meal_id, sample_meal.user_id
        )
        assert len(retrieved.components) == 2


@pytest.mark.asyncio
class TestMongoMealRepositoryGet:
    """Test retrieval operations."""

    async def test_get_by_id_existing(self, mongo_repo, sample_meal):
        """Should retrieve existing meal by ID."""
        await mongo_repo.save(sample_meal)

        retrieved = await mongo_repo.get_by_id(
            sample_meal.meal_id, sample_meal.user_id
        )
        assert retrieved is not None
        assert retrieved.meal_id == sample_meal.meal_id

    async def test_get_by_id_nonexistent(self, mongo_repo):
        """Should return None for nonexistent meal."""
        retrieved = await mongo_repo.get_by_id(
            "nonexistent_id", "test_user_001"
        )
        assert retrieved is None

    async def test_list_by_user_empty(self, mongo_repo):
        """Should return empty list for user with no meals."""
        meals = await mongo_repo.list_by_user("test_user_999")
        assert meals == []

    async def test_list_by_user_with_meals(self, mongo_repo, sample_meal):
        """Should return all meals for a user."""
        await mongo_repo.save(sample_meal)

        # Add second meal
        meal2 = MealEntry(
            meal_id="test_meal_002",
            user_id="test_user_001",
            timestamp=datetime(2025, 11, 12, 18, 0, 0, tzinfo=timezone.utc),
            components=[],
        )
        await mongo_repo.save(meal2)

        meals = await mongo_repo.list_by_user("test_user_001")
        assert len(meals) == 2

    async def test_list_by_user_pagination(self, mongo_repo):
        """Should support pagination."""
        # Create 5 meals
        for i in range(5):
            meal = MealEntry(
                meal_id=f"test_meal_{i:03d}",
                user_id="test_user_pagination",
                timestamp=datetime(
                    2025, 11, 12, 10 + i, 0, 0, tzinfo=timezone.utc
                ),
                components=[],
            )
            await mongo_repo.save(meal)

        # Get first page
        page1 = await mongo_repo.list_by_user(
            "test_user_pagination", limit=2, skip=0
        )
        assert len(page1) == 2

        # Get second page
        page2 = await mongo_repo.list_by_user(
            "test_user_pagination", limit=2, skip=2
        )
        assert len(page2) == 2

        # Verify different meals
        assert page1[0].meal_id != page2[0].meal_id


@pytest.mark.asyncio
class TestMongoMealRepositoryDelete:
    """Test delete operations."""

    async def test_delete_existing_meal(self, mongo_repo, sample_meal):
        """Should successfully delete existing meal."""
        await mongo_repo.save(sample_meal)

        # Verify exists
        retrieved = await mongo_repo.get_by_id(
            sample_meal.meal_id, sample_meal.user_id
        )
        assert retrieved is not None

        # Delete
        await mongo_repo.delete(sample_meal.meal_id, sample_meal.user_id)

        # Verify deleted
        retrieved = await mongo_repo.get_by_id(
            sample_meal.meal_id, sample_meal.user_id
        )
        assert retrieved is None

    async def test_delete_nonexistent_meal_no_error(self, mongo_repo):
        """Should not raise error when deleting nonexistent meal."""
        # Should not raise
        await mongo_repo.delete("nonexistent_id", "test_user_001")


@pytest.mark.asyncio
class TestMongoMealRepositorySearch:
    """Test search operations."""

    async def test_search_by_date_range(self, mongo_repo):
        """Should find meals within date range."""
        # Create meals on different days
        for day in [10, 11, 12]:
            meal = MealEntry(
                meal_id=f"test_meal_day_{day}",
                user_id="test_user_search",
                timestamp=datetime(
                    2025, 11, day, 12, 0, 0, tzinfo=timezone.utc
                ),
                components=[],
            )
            await mongo_repo.save(meal)

        # Search for specific day range
        start = datetime(2025, 11, 11, 0, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 11, 11, 23, 59, 59, tzinfo=timezone.utc)

        meals = await mongo_repo.search(
            user_id="test_user_search", start_date=start, end_date=end
        )

        assert len(meals) == 1
        assert meals[0].meal_id == "test_meal_day_11"

    async def test_search_no_filters_returns_all(self, mongo_repo):
        """Should return all user meals when no filters specified."""
        # Create 3 meals
        for i in range(3):
            meal = MealEntry(
                meal_id=f"test_meal_{i:03d}",
                user_id="test_user_all",
                timestamp=datetime(
                    2025, 11, 12, 10 + i, 0, 0, tzinfo=timezone.utc
                ),
                components=[],
            )
            await mongo_repo.save(meal)

        meals = await mongo_repo.search(user_id="test_user_all")
        assert len(meals) == 3
