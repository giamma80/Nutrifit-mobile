"""MealUpdated domain event.

Event raised when a meal or its entries have been updated.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List
from uuid import UUID, uuid4

from .base import DomainEvent


@dataclass(frozen=True)
class MealUpdated(DomainEvent):
    """Domain event: Meal has been updated.

    Raised when meal properties or entries are modified after
    initial creation/analysis. Tracks which fields were changed.

    Attributes:
        meal_id: ID of the updated meal.
        user_id: ID of the user who updated the meal.
        updated_fields: List of field names that were updated.

    Examples:
        >>> event = MealUpdated.create(
        ...     meal_id=uuid4(),
        ...     user_id="user-123",
        ...     updated_fields=["quantity_g", "calories"]
        ... )
        >>> "quantity_g" in event.updated_fields
        True
    """

    meal_id: UUID
    user_id: str
    updated_fields: List[str]

    @classmethod
    def create(
        cls,
        meal_id: UUID,
        user_id: str,
        updated_fields: List[str],
    ) -> "MealUpdated":
        """Create new MealUpdated event.

        Args:
            meal_id: ID of the updated meal.
            user_id: ID of the user who updated the meal.
            updated_fields: List of field names that were updated (non-empty).

        Returns:
            New MealUpdated event with generated event_id and current timestamp.

        Raises:
            ValueError: If updated_fields is empty.
        """
        if not updated_fields:
            raise ValueError("updated_fields cannot be empty")

        return cls(
            event_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            meal_id=meal_id,
            user_id=user_id,
            updated_fields=list(updated_fields),  # Copy to ensure immutability
        )
