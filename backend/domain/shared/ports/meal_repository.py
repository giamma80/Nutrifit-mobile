"""Meal repository port (interface).

Defines contract for meal persistence operations.
Follows the Dependency Inversion Principle: domain defines the port,
infrastructure provides the implementation.
"""

from typing import Optional, Protocol, List
from datetime import datetime
from uuid import UUID

from domain.meal.core.entities.meal import Meal


class IMealRepository(Protocol):
    """
    Interface for meal persistence operations.

    This port defines the contract that infrastructure adapters must implement
    to provide meal storage functionality. Examples of implementations:
    - In-memory repository (for testing)
    - MongoDB repository (for production)
    - PostgreSQL repository (alternative)

    Example implementation (infrastructure layer):
        >>> class InMemoryMealRepository:
        ...     async def save(self, meal: Meal) -> None:
        ...         self._storage[meal.id] = meal
        ...
        ...     async def get_by_id(self, meal_id: UUID) -> Optional[Meal]:
        ...         return self._storage.get(meal_id)

    Example usage (application layer):
        >>> class CreateMealCommandHandler:
        ...     def __init__(self, repository: IMealRepository):
        ...         self._repository = repository
        ...
        ...     async def handle(self, command: CreateMealCommand) -> Meal:
        ...         meal = Meal(...)
        ...         await self._repository.save(meal)
        ...         return meal
    """

    async def save(self, meal: Meal) -> None:
        """
        Save or update a meal.

        Args:
            meal: Meal entity to save

        Note:
            - If meal.id exists in storage, updates the existing meal
            - If meal.id is new, creates a new meal
            - Updates meal.updated_at timestamp

        Example:
            >>> meal = Meal(id=uuid4(), user_id="user123", ...)
            >>> await repository.save(meal)
        """
        ...

    async def get_by_id(self, meal_id: UUID, user_id: str) -> Optional[Meal]:
        """
        Retrieve meal by ID for a specific user.

        Args:
            meal_id: Unique meal identifier
            user_id: User identifier (for authorization)

        Returns:
            Meal if found and belongs to user, None otherwise

        Example:
            >>> meal = await repository.get_by_id(
            ...     UUID("..."),
            ...     user_id="user123"
            ... )
            >>> if meal:
            ...     print(f"Found meal: {meal.meal_type}")
        """
        ...

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
            limit: Maximum number of meals to return (default: 100)
            offset: Number of meals to skip (default: 0)

        Returns:
            List of meals ordered by timestamp descending (newest first)

        Example:
            >>> meals = await repository.get_by_user(
            ...     user_id="user123",
            ...     limit=10,
            ...     offset=0
            ... )
            >>> print(f"Retrieved {len(meals)} meals")
        """
        ...

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
            List of meals ordered by timestamp ascending

        Example:
            >>> from datetime import datetime, timezone, timedelta
            >>> today = datetime.now(timezone.utc)
            >>> yesterday = today - timedelta(days=1)
            >>> meals = await repository.get_by_user_and_date_range(
            ...     user_id="user123",
            ...     start_date=yesterday,
            ...     end_date=today
            ... )
        """
        ...

    async def delete(self, meal_id: UUID, user_id: str) -> bool:
        """
        Delete a meal (soft delete recommended in implementation).

        Args:
            meal_id: Unique meal identifier
            user_id: User identifier (for authorization)

        Returns:
            True if meal was deleted, False if not found or unauthorized

        Example:
            >>> deleted = await repository.delete(
            ...     UUID("..."),
            ...     user_id="user123"
            ... )
            >>> if deleted:
            ...     print("Meal deleted successfully")
        """
        ...

    async def exists(self, meal_id: UUID, user_id: str) -> bool:
        """
        Check if a meal exists for a user.

        Args:
            meal_id: Unique meal identifier
            user_id: User identifier (for authorization)

        Returns:
            True if meal exists and belongs to user, False otherwise

        Example:
            >>> if await repository.exists(UUID("..."), "user123"):
            ...     print("Meal exists")
        """
        ...

    async def count_by_user(self, user_id: str) -> int:
        """
        Count total meals for a user.

        Args:
            user_id: User identifier

        Returns:
            Total number of meals for user

        Example:
            >>> total = await repository.count_by_user("user123")
            >>> print(f"User has {total} meals")
        """
        ...
