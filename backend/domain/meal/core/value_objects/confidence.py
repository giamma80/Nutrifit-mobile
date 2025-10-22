"""Confidence value object.

Immutable confidence score for AI predictions.
Enforces 0.0-1.0 range and provides semantic constructors.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Confidence:
    """Value object for confidence score (0.0 - 1.0).

    Immutable confidence score for AI/ML predictions.
    Validates range and provides semantic interpretation.

    Attributes:
        value: Confidence score between 0.0 and 1.0.

    Examples:
        >>> c = Confidence(0.85)
        >>> c.is_reliable()
        True

        >>> high = Confidence.high()
        >>> float(high)
        0.9

        >>> low = Confidence.low()
        >>> low.is_reliable()
        False

    Raises:
        ValueError: If value is not in [0.0, 1.0] range.
    """

    value: float

    def __post_init__(self) -> None:
        """Validate confidence invariants."""
        if not 0.0 <= self.value <= 1.0:
            raise ValueError(
                f"Confidence must be between 0.0 and 1.0, got {self.value}"
            )

    @classmethod
    def high(cls) -> "Confidence":
        """High confidence (>0.8).

        Returns:
            Confidence instance with high value (0.9).
        """
        return cls(0.9)

    @classmethod
    def medium(cls) -> "Confidence":
        """Medium confidence (0.5-0.8).

        Returns:
            Confidence instance with medium value (0.7).
        """
        return cls(0.7)

    @classmethod
    def low(cls) -> "Confidence":
        """Low confidence (<0.5).

        Returns:
            Confidence instance with low value (0.4).
        """
        return cls(0.4)

    def is_reliable(self) -> bool:
        """Check if confidence is reliable (>0.7).

        Threshold based on empirical observation that predictions
        with confidence >0.7 are acceptable for food recognition.

        Returns:
            True if confidence > 0.7.
        """
        return self.value > 0.7

    def __float__(self) -> float:
        """Convert to float for numeric operations."""
        return self.value

    def __str__(self) -> str:
        """Human-readable representation as percentage."""
        return f"{self.value * 100:.1f}%"

    def __repr__(self) -> str:
        """Developer representation."""
        return f"Confidence({self.value})"
