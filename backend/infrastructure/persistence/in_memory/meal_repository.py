"""In-memory meal repository implementation.

Provides an in-memory implementation of IMealRepository port for testing.
Uses a dictionary for storage with no external dependencies.
"""

from typing import Optional, Dict, List
from datetime import datetime, timezone
from uuid import UUID
from copy import deepcopy

from domain.meal.core.entities.meal import Meal


class InMemoryMealRepository:
    """
    In-memory implementation of IMealRepository port.

    This adapter provides a dictionary-based storage for meals,
    implementing the IMealRepository port defined by the domain layer.

    Thread safety: NOT thread-safe (use locks if needed in production)
    Persistence: Data lost on process restart (in-memory only)

    Example:
        >>> repository = InMemoryMealRepository()
        >>> meal = Meal(id=uuid4(), user_id="user123", ...)
        >>> await repository.save(meal)
        >>> retrieved = await repository.get_by_id(meal.id, "user123")
    """

    def __init__(self) -> None:
        """Initialize repository with empty storage."""
        self._storage: Dict[UUID, Meal] = {}

    async def save(self, meal: Meal) -> None:
        """
        Save or update a meal in memory.

        Args:
            meal: Meal entity to save

        Note:
            - Stores a deep copy to prevent external modifications
            - Updates meal.updated_at to current UTC time
        """
        # Update timestamp
        meal.updated_at = datetime.now(timezone.utc)

        # Store deep copy to prevent external modifications
        self._storage[meal.id] = deepcopy(meal)

    async def get_by_id(
        self, meal_id: UUID, user_id: str
    ) -> Optional[Meal]:
        """
        Retrieve meal by ID for a specific user.

        Args:
            meal_id: Unique meal identifier
            user_id: User identifier (for authorization)

        Returns:
            Deep copy of Meal if found and belongs to user, None otherwise
        """
        meal = self._storage.get(meal_id)

        # Authorization check: meal must belong to user
        if meal is None or meal.user_id != user_id:
            return None

        # Return deep copy to prevent external modifications
        return deepcopy(meal)

    async def get_by_user(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Meal]:
        """
        Get meals for a user with pagination.

        Args:
            user_id: User identifier
            limit: Maximum number of meals to return
            offset: Number of meals to skip

        Returns:
            List of meal deep copies ordered by timestamp descending
        """
        # Filter by user
        user_meals = [
            meal for meal in self._storage.values()
            if meal.user_id == user_id
        ]

        # Sort by timestamp descending (newest first)
        user_meals.sort(key=lambda m: m.timestamp, reverse=True)

        # Apply pagination
        paginated = user_meals[offset:offset + limit]

        # Return deep copies
        return [deepcopy(meal) for meal in paginated]

    async def get_by_user_and_date_range(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Meal]:
        """
        Get meals for a user within a date range.

        Args:
            user_id: User identifier
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)

        Returns:
            List of meal deep copies ordered by timestamp ascending
        """
        # Filter by user and date range
        filtered_meals = [
            meal for meal in self._storage.values()
            if meal.user_id == user_id
            and start_date <= meal.timestamp <= end_date
        ]

        # Sort by timestamp ascending (oldest first)
        filtered_meals.sort(key=lambda m: m.timestamp)

        # Return deep copies
        return [deepcopy(meal) for meal in filtered_meals]

    async def delete(self, meal_id: UUID, user_id: str) -> bool:
        """
        Delete a meal from memory.

        Args:
            meal_id: Unique meal identifier
            user_id: User identifier (for authorization)

        Returns:
            True if meal was deleted, False if not found or unauthorized
        """
        meal = self._storage.get(meal_id)

        # Authorization check: meal must exist and belong to user
        if meal is None or meal.user_id != user_id:
            return False

        # Delete from storage
        del self._storage[meal_id]
        return True

    async def exists(self, meal_id: UUID, user_id: str) -> bool:
        """
        Check if a meal exists for a user.

        Args:
            meal_id: Unique meal identifier
            user_id: User identifier (for authorization)

        Returns:
            True if meal exists and belongs to user, False otherwise
        """
        meal = self._storage.get(meal_id)
        return meal is not None and meal.user_id == user_id

    async def count_by_user(self, user_id: str) -> int:
        """
        Count total meals for a user.

        Args:
            user_id: User identifier

        Returns:
            Total number of meals for user
        """
        return sum(
            1 for meal in self._storage.values()
            if meal.user_id == user_id
        )

    def clear(self) -> None:
        """
        Clear all meals from storage.

        Note: Utility method for testing - not part of IMealRepository port
        """
        self._storage.clear()
