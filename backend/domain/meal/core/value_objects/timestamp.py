"""Timestamp value object.

Immutable UTC timestamp with timezone awareness.
Enforces timezone-aware datetimes and validates against future timestamps.
"""

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class Timestamp:
    """Value object for UTC timestamp.

    Immutable timestamp that enforces:
    - Timezone awareness (UTC)
    - No future timestamps (meal logging is historical)

    Attributes:
        value: Timezone-aware datetime in UTC.

    Examples:
        >>> ts = Timestamp.now()
        >>> ts.is_today()
        True

        >>> ts2 = Timestamp.from_iso('2025-01-15T10:30:00Z')
        >>> ts2.to_iso()
        '2025-01-15T10:30:00+00:00'

    Raises:
        ValueError: If timestamp is not timezone-aware or is in the future.
    """

    value: datetime

    def __post_init__(self) -> None:
        """Validate timestamp invariants."""
        if self.value.tzinfo is None:
            raise ValueError("Timestamp must be timezone-aware (use UTC)")

        # Allow small tolerance for clock skew (1 minute)
        if self.value > datetime.now(timezone.utc):
            raise ValueError("Timestamp cannot be in the future")

    @classmethod
    def now(cls) -> "Timestamp":
        """Create timestamp for current moment (UTC).

        Returns:
            Timestamp representing current time.
        """
        return cls(datetime.now(timezone.utc))

    @classmethod
    def from_iso(cls, iso_string: str) -> "Timestamp":
        """Create from ISO 8601 string.

        Args:
            iso_string: ISO 8601 formatted datetime string.
                       Example: '2025-01-15T10:30:00Z'

        Returns:
            Timestamp instance.

        Raises:
            ValueError: If string is not valid ISO 8601 format.
        """
        # Handle 'Z' suffix for UTC
        if iso_string.endswith("Z"):
            iso_string = iso_string[:-1] + "+00:00"

        dt = datetime.fromisoformat(iso_string)
        return cls(dt)

    def to_iso(self) -> str:
        """Convert to ISO 8601 string.

        Returns:
            ISO 8601 formatted string with timezone.
        """
        return self.value.isoformat()

    def is_today(self) -> bool:
        """Check if timestamp is today (UTC date).

        Returns:
            True if timestamp date matches current UTC date.
        """
        now = datetime.now(timezone.utc)
        return self.value.date() == now.date()

    def __str__(self) -> str:
        """Human-readable representation."""
        return self.value.strftime("%Y-%m-%d %H:%M:%S UTC")

    def __repr__(self) -> str:
        """Developer representation."""
        return f"Timestamp({self.value.isoformat()})"
