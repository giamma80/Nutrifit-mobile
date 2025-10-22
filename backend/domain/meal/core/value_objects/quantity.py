"""Quantity value object.

Immutable representation of food quantity with unit and conversions.
Enforces positive values and supports common cooking units.
"""

from dataclasses import dataclass
from typing import Literal

# Supported units for quantity
Unit = Literal["g", "ml", "oz", "cup", "tbsp", "tsp"]


@dataclass(frozen=True)
class Quantity:
    """Value object for quantity with unit.

    Immutable quantity that validates positive values and
    provides unit conversions to grams (base unit).

    Attributes:
        value: Numeric amount (must be positive)
        unit: Unit of measurement (defaults to grams)

    Examples:
        >>> q = Quantity(100.0, "g")
        >>> q.to_grams()
        100.0

        >>> q2 = Quantity(2.0, "cup")
        >>> q2.to_grams()
        480.0

        >>> q.scale(2.0)
        Quantity(value=200.0, unit='g')

    Raises:
        ValueError: If value is not positive or unit is invalid.
    """

    value: float
    unit: Unit = "g"

    def __post_init__(self) -> None:
        """Validate quantity invariants."""
        if self.value <= 0:
            raise ValueError(f"Quantity must be positive, got {self.value}")

        if self.unit not in ["g", "ml", "oz", "cup", "tbsp", "tsp"]:
            raise ValueError(f"Invalid unit: {self.unit}")

    def to_grams(self) -> float:
        """Convert to grams (base unit).

        Uses standard conversion factors. For liquids (ml), assumes
        density ~1.0 (water equivalent).

        Returns:
            Quantity in grams.
        """
        conversions = {
            "g": 1.0,
            "ml": 1.0,  # Assume density ~1 for liquids
            "oz": 28.35,
            "cup": 240.0,
            "tbsp": 15.0,
            "tsp": 5.0,
        }
        return self.value * conversions[self.unit]

    def scale(self, factor: float) -> "Quantity":
        """Scale quantity by factor.

        Args:
            factor: Scaling factor (e.g., 2.0 for double).

        Returns:
            New Quantity with scaled value.

        Raises:
            ValueError: If resulting quantity would be non-positive.
        """
        return Quantity(self.value * factor, self.unit)

    def __str__(self) -> str:
        """Human-readable representation."""
        return f"{self.value:.1f}{self.unit}"

    def __repr__(self) -> str:
        """Developer representation."""
        return f"Quantity(value={self.value}, unit='{self.unit}')"
