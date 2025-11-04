"""Unit tests for SearchMealsQuery and handler."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from application.meal.queries.search_meals import (
    SearchMealsQuery,
    SearchMealsQueryHandler,
)
from domain.meal.core.entities.meal import Meal


@pytest.fixture
def mock_repository():
    return AsyncMock()


@pytest.fixture
def handler(mock_repository):
    return SearchMealsQueryHandler(repository=mock_repository)


@pytest.fixture
def sample_meals_for_search():
    """Create meals with different entry names for search testing."""
    meals = []

    # Meal 1: Pasta
    meal1 = MagicMock(spec=Meal)
    meal1.id = uuid4()
    meal1.user_id = "user123"
    meal1.meal_type = "LUNCH"
    meal1.notes = None
    entry1 = MagicMock()
    entry1.name = "pasta"
    entry1.display_name = "Spaghetti"
    meal1.entries = [entry1]
    meals.append(meal1)

    # Meal 2: Chicken
    meal2 = MagicMock(spec=Meal)
    meal2.id = uuid4()
    meal2.user_id = "user123"
    meal2.meal_type = "DINNER"
    meal2.notes = "Grilled with vegetables"
    entry2 = MagicMock()
    entry2.name = "chicken"
    entry2.display_name = "Chicken Breast"
    meal2.entries = [entry2]
    meals.append(meal2)

    # Meal 3: Salad
    meal3 = MagicMock(spec=Meal)
    meal3.id = uuid4()
    meal3.user_id = "user123"
    meal3.meal_type = "LUNCH"
    meal3.notes = "Fresh salad with chicken"
    entry3 = MagicMock()
    entry3.name = "salad"
    entry3.display_name = "Mixed Salad"
    meal3.entries = [entry3]
    meals.append(meal3)

    return meals


class TestSearchMealsQueryHandler:
    """Test SearchMealsQueryHandler."""

    @pytest.mark.asyncio
    async def test_search_by_entry_name(self, handler, mock_repository, sample_meals_for_search):
        """Test searching by entry name."""
        query = SearchMealsQuery(user_id="user123", query_text="pasta")

        mock_repository.get_by_user.return_value = sample_meals_for_search

        result = await handler.handle(query)

        # Should find 1 meal with pasta
        assert len(result) == 1
        assert "pasta" in result[0].entries[0].name.lower()

    @pytest.mark.asyncio
    async def test_search_by_display_name(self, handler, mock_repository, sample_meals_for_search):
        """Test searching by display name."""
        query = SearchMealsQuery(user_id="user123", query_text="chicken")

        mock_repository.get_by_user.return_value = sample_meals_for_search

        result = await handler.handle(query)

        # Should find 2 meals (one with "chicken" entry, one with "chicken" in notes)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_search_by_notes(self, handler, mock_repository, sample_meals_for_search):
        """Test searching in meal notes."""
        query = SearchMealsQuery(user_id="user123", query_text="grilled")

        mock_repository.get_by_user.return_value = sample_meals_for_search

        result = await handler.handle(query)

        # Should find 1 meal with "grilled" in notes
        assert len(result) == 1
        assert "grilled" in result[0].notes.lower()

    @pytest.mark.asyncio
    async def test_search_case_insensitive(self, handler, mock_repository, sample_meals_for_search):
        """Test case-insensitive search."""
        query = SearchMealsQuery(user_id="user123", query_text="PASTA")

        mock_repository.get_by_user.return_value = sample_meals_for_search

        result = await handler.handle(query)

        # Should find pasta meal despite uppercase query
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_search_no_results(self, handler, mock_repository, sample_meals_for_search):
        """Test search with no matching results."""
        query = SearchMealsQuery(user_id="user123", query_text="pizza")

        mock_repository.get_by_user.return_value = sample_meals_for_search

        result = await handler.handle(query)

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_search_with_pagination(self, handler, mock_repository, sample_meals_for_search):
        """Test search with pagination."""
        query = SearchMealsQuery(user_id="user123", query_text="chicken", limit=1, offset=0)

        mock_repository.get_by_user.return_value = sample_meals_for_search

        result = await handler.handle(query)

        # Should return only 1 result due to limit
        assert len(result) == 1
