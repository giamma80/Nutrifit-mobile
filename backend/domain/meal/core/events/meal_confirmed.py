"""MealConfirmed domain event.

Event raised when a user confirms or rejects analyzed meal entries.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

from .base import DomainEvent


@dataclass(frozen=True)
class MealConfirmed(DomainEvent):
    """Domain event: Meal has been confirmed by user.

    Raised when a user reviews analyzed meal entries and confirms
    or rejects them. This event captures the user's feedback on
    the AI analysis.

    Attributes:
        meal_id: ID of the confirmed meal.
        user_id: ID of the user who confirmed the meal.
        confirmed_entry_count: Number of entries user confirmed/kept.
        rejected_entry_count: Number of entries user rejected/removed.

    Examples:
        >>> event = MealConfirmed.create(
        ...     meal_id=uuid4(),
        ...     user_id="user-123",
        ...     confirmed_entry_count=2,
        ...     rejected_entry_count=1
        ... )
        >>> event.confirmed_entry_count
        2
    """

    meal_id: UUID
    user_id: str
    confirmed_entry_count: int
    rejected_entry_count: int

    @classmethod
    def create(
        cls,
        meal_id: UUID,
        user_id: str,
        confirmed_entry_count: int,
        rejected_entry_count: int,
    ) -> "MealConfirmed":
        """Create new MealConfirmed event.

        Args:
            meal_id: ID of the confirmed meal.
            user_id: ID of the user who confirmed the meal.
            confirmed_entry_count: Number of entries confirmed (>= 0).
            rejected_entry_count: Number of entries rejected (>= 0).

        Returns:
            New MealConfirmed event with generated event_id and current timestamp.

        Raises:
            ValueError: If any count is negative.
        """
        if confirmed_entry_count < 0:
            raise ValueError(
                f"confirmed_entry_count cannot be negative, got {confirmed_entry_count}"
            )

        if rejected_entry_count < 0:
            raise ValueError(f"rejected_entry_count cannot be negative, got {rejected_entry_count}")

        return cls(
            event_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            meal_id=meal_id,
            user_id=user_id,
            confirmed_entry_count=confirmed_entry_count,
            rejected_entry_count=rejected_entry_count,
        )
