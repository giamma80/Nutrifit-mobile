"""MealId value object.

Immutable identifier for Meal aggregate root.
Uses UUID for global uniqueness and database-friendly format.
"""

from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True)
class MealId:
    """Value object for Meal ID.

    Immutable identifier using UUID. Frozen dataclass ensures
    immutability and provides equality by value.

    Examples:
        >>> meal_id = MealId.generate()
        >>> str(meal_id)
        '3fa85f64-5717-4562-b3fc-2c963f66afa6'

        >>> meal_id2 = MealId.from_string('3fa85f64-5717-4562-b3fc-2c963f66afa6')
        >>> meal_id == meal_id2
        True
    """

    value: UUID

    @classmethod
    def generate(cls) -> "MealId":
        """Generate new meal ID with UUID4.

        Returns:
            New MealId with random UUID.
        """
        return cls(uuid4())

    @classmethod
    def from_string(cls, id_str: str) -> "MealId":
        """Create MealId from string representation.

        Args:
            id_str: String representation of UUID.

        Returns:
            MealId instance.

        Raises:
            ValueError: If string is not valid UUID format.
        """
        return cls(UUID(id_str))

    def __str__(self) -> str:
        """String representation as UUID string."""
        return str(self.value)

    def __repr__(self) -> str:
        """Developer representation."""
        return f"MealId({self.value})"
