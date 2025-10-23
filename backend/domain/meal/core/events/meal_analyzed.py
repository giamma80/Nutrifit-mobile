"""MealAnalyzed domain event.

Event raised when a meal has been analyzed from a source
(photo, barcode, or description).
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

from .base import DomainEvent


@dataclass(frozen=True)
class MealAnalyzed(DomainEvent):
    """Domain event: Meal has been analyzed.

    Raised when meal analysis completes successfully, indicating
    that food items have been identified and nutritional data extracted.

    Attributes:
        meal_id: ID of the analyzed meal.
        user_id: ID of the user who owns the meal.
        source: Source of analysis (PHOTO | BARCODE | DESCRIPTION).
        item_count: Number of food items identified.
        average_confidence: Average confidence score across all items.

    Examples:
        >>> event = MealAnalyzed.create(
        ...     meal_id=uuid4(),
        ...     user_id="user-123",
        ...     source="PHOTO",
        ...     item_count=3,
        ...     average_confidence=0.85
        ... )
        >>> event.source
        'PHOTO'
    """

    meal_id: UUID
    user_id: str
    source: str  # PHOTO | BARCODE | DESCRIPTION
    item_count: int
    average_confidence: float

    @classmethod
    def create(
        cls,
        meal_id: UUID,
        user_id: str,
        source: str,
        item_count: int,
        average_confidence: float,
    ) -> "MealAnalyzed":
        """Create new MealAnalyzed event.

        Args:
            meal_id: ID of the analyzed meal.
            user_id: ID of the user who owns the meal.
            source: Source of analysis (PHOTO, BARCODE, or DESCRIPTION).
            item_count: Number of food items identified (must be > 0).
            average_confidence: Average confidence score (0.0 - 1.0).

        Returns:
            New MealAnalyzed event with generated event_id and current timestamp.

        Raises:
            ValueError: If item_count <= 0 or average_confidence not in [0, 1].
        """
        if item_count <= 0:
            raise ValueError(f"item_count must be positive, got {item_count}")

        if not 0.0 <= average_confidence <= 1.0:
            raise ValueError(
                f"average_confidence must be between 0.0 and 1.0, " f"got {average_confidence}"
            )

        if source not in ["PHOTO", "BARCODE", "DESCRIPTION"]:
            raise ValueError(f"Invalid source: {source}")

        return cls(
            event_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            meal_id=meal_id,
            user_id=user_id,
            source=source,
            item_count=item_count,
            average_confidence=average_confidence,
        )
