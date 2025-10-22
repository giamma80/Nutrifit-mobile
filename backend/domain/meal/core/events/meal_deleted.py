"""MealDeleted domain event.

Event raised when a meal is deleted by the user.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

from .base import DomainEvent


@dataclass(frozen=True)
class MealDeleted(DomainEvent):
    """Domain event: Meal has been deleted.

    Raised when a user deletes a meal. This is a soft delete
    event - the actual data may be retained for audit purposes.

    Attributes:
        meal_id: ID of the deleted meal.
        user_id: ID of the user who deleted the meal.

    Examples:
        >>> event = MealDeleted.create(
        ...     meal_id=uuid4(),
        ...     user_id="user-123"
        ... )
        >>> event.user_id
        'user-123'
    """

    meal_id: UUID
    user_id: str

    @classmethod
    def create(
        cls,
        meal_id: UUID,
        user_id: str,
    ) -> "MealDeleted":
        """Create new MealDeleted event.

        Args:
            meal_id: ID of the deleted meal.
            user_id: ID of the user who deleted the meal.

        Returns:
            New MealDeleted event with generated event_id and current timestamp.
        """
        return cls(
            event_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            meal_id=meal_id,
            user_id=user_id,
        )
