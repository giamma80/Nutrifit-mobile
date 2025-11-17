"""UserId value object."""

from dataclasses import dataclass
import uuid


@dataclass(frozen=True)
class UserId:
    """User identifier value object.

    Internal UUID for user identification within the system.
    Immutable and unique.

    Examples:
        >>> user_id = UserId.generate()
        >>> str(user_id)
        'e4b8c9d0-1234-5678-9abc-def012345678'

        >>> user_id = UserId("e4b8c9d0-1234-5678-9abc-def012345678")
        >>> user_id.value
        'e4b8c9d0-1234-5678-9abc-def012345678'
    """

    value: str

    def __post_init__(self) -> None:
        """Validate UUID format."""
        try:
            uuid.UUID(self.value)
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid UUID format: {self.value}") from e

    @staticmethod
    def generate() -> "UserId":
        """Generate a new random UserId.

        Returns:
            New UserId with random UUID v4
        """
        return UserId(str(uuid.uuid4()))

    def __str__(self) -> str:
        """String representation returns the UUID value."""
        return self.value

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"UserId('{self.value}')"
