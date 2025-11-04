"""Unit tests for GetMealQuery and handler."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from application.meal.queries.get_meal import (
    GetMealQuery,
    GetMealQueryHandler,
)
from domain.meal.core.entities.meal import Meal


@pytest.fixture
def mock_repository():
    return AsyncMock()


@pytest.fixture
def handler(mock_repository):
    return GetMealQueryHandler(repository=mock_repository)


@pytest.fixture
def sample_meal():
    meal = MagicMock(spec=Meal)
    meal.id = uuid4()
    meal.user_id = "user123"
    meal.meal_type = "LUNCH"
    meal.entries = [MagicMock(), MagicMock()]
    return meal


class TestGetMealQueryHandler:
    """Test GetMealQueryHandler."""

    @pytest.mark.asyncio
    async def test_get_meal_success(self, handler, mock_repository, sample_meal):
        """Test successful meal retrieval."""
        query = GetMealQuery(meal_id=sample_meal.id, user_id="user123")

        mock_repository.get_by_id.return_value = sample_meal

        result = await handler.handle(query)

        assert result == sample_meal
        mock_repository.get_by_id.assert_called_once_with(sample_meal.id, "user123")

    @pytest.mark.asyncio
    async def test_get_meal_not_found(self, handler, mock_repository):
        """Test meal not found."""
        meal_id = uuid4()
        query = GetMealQuery(meal_id=meal_id, user_id="user123")

        mock_repository.get_by_id.return_value = None

        result = await handler.handle(query)

        assert result is None
        mock_repository.get_by_id.assert_called_once_with(meal_id, "user123")

    @pytest.mark.asyncio
    async def test_get_meal_authorization(self, handler, mock_repository, sample_meal):
        """Test authorization - different user."""
        query = GetMealQuery(meal_id=sample_meal.id, user_id="different_user")

        # Repository returns None for unauthorized access
        mock_repository.get_by_id.return_value = None

        result = await handler.handle(query)

        assert result is None
        mock_repository.get_by_id.assert_called_once_with(sample_meal.id, "different_user")
