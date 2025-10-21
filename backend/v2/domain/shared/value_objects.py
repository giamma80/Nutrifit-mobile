"""
Shared value objects.

Immutable, validated domain primitives.
Following DDD value object pattern.
"""

from __future__ import annotations

import re
import uuid
from pydantic import BaseModel, Field, field_validator, ConfigDict


class UserId(BaseModel):
    """
    User ID value object.

    Wraps string ID with validation and type safety.

    Example:
        >>> user_id = UserId(value="user_123")
        >>> assert str(user_id) == "user_123"
        >>> user_id2 = UserId.from_string("user_456")
    """

    model_config = ConfigDict(frozen=True)

    value: str = Field(..., min_length=1, description="User identifier")

    @field_validator("value")
    @classmethod
    def not_empty(cls, v: str) -> str:
        """Ensure not empty or whitespace."""
        if not v.strip():
            raise ValueError("UserId cannot be empty or whitespace")
        return v.strip()

    def __str__(self) -> str:
        """String representation."""
        return self.value

    def __repr__(self) -> str:
        """Debug representation."""
        return f"UserId('{self.value}')"

    def __hash__(self) -> int:
        """Allow use as dict key."""
        return hash(self.value)

    @classmethod
    def from_string(cls, s: str) -> UserId:
        """Create from string."""
        return cls(value=s)


class Barcode(BaseModel):
    """
    Product barcode value object.

    Validates barcode format (8-13 digits).
    Used for OpenFoodFacts lookups.

    Example:
        >>> barcode = Barcode(value="3017620422003")
        >>> assert len(barcode.value) == 13
        >>> assert barcode.is_valid()
    """

    model_config = ConfigDict(frozen=True)

    value: str = Field(..., pattern=r"^\d{8,13}$", description="Barcode digits")

    def __str__(self) -> str:
        """String representation."""
        return self.value

    def __repr__(self) -> str:
        """Debug representation."""
        return f"Barcode('{self.value}')"

    def __hash__(self) -> int:
        """Allow use as dict key."""
        return hash(self.value)

    def is_valid(self) -> bool:
        """
        Validate barcode format.

        Returns:
            True if valid (8-13 digits)
        """
        return bool(re.match(r"^\d{8,13}$", self.value))

    @classmethod
    def from_string(cls, s: str) -> Barcode:
        """Create from string."""
        return cls(value=s)


class AnalysisId(BaseModel):
    """
    Analysis ID value object.

    Identifies temporary meal analyses.
    Format: "analysis_<12_hex_chars>"

    Example:
        >>> analysis_id = AnalysisId.generate()
        >>> assert analysis_id.value.startswith("analysis_")
        >>> assert len(analysis_id.value) == 21  # "analysis_" + 12 chars
    """

    model_config = ConfigDict(frozen=True)

    value: str = Field(
        ...,
        pattern=r"^analysis_[a-f0-9]{12}$",
        description="Analysis identifier",
    )

    def __str__(self) -> str:
        """String representation."""
        return self.value

    def __repr__(self) -> str:
        """Debug representation."""
        return f"AnalysisId('{self.value}')"

    def __hash__(self) -> int:
        """Allow use as dict key."""
        return hash(self.value)

    @classmethod
    def generate(cls) -> AnalysisId:
        """
        Generate new analysis ID.

        Returns:
            New AnalysisId with random UUID

        Example:
            >>> id1 = AnalysisId.generate()
            >>> id2 = AnalysisId.generate()
            >>> assert id1 != id2
        """
        random_part = uuid.uuid4().hex[:12]
        return cls(value=f"analysis_{random_part}")

    @classmethod
    def from_string(cls, s: str) -> AnalysisId:
        """Create from string."""
        return cls(value=s)


class MealId(BaseModel):
    """
    Meal ID value object.

    Identifies persistent meal entries.
    Usually MongoDB ObjectId as string.

    Example:
        >>> meal_id = MealId(value="507f1f77bcf86cd799439011")
        >>> assert len(meal_id.value) == 24
    """

    value: str = Field(..., min_length=1, description="Meal identifier")

    def __str__(self) -> str:
        """String representation."""
        return self.value

    def __repr__(self) -> str:
        """Debug representation."""
        return f"MealId('{self.value}')"

    def __hash__(self) -> int:
        """Allow use as dict key."""
        return hash(self.value)

    @classmethod
    def generate(cls) -> MealId:
        """
        Generate new meal ID.

        Note: In production, MongoDB generates ObjectIds.
        This generates a UUID for testing.

        Returns:
            New MealId
        """
        return cls(value=str(uuid.uuid4()))

    @classmethod
    def from_string(cls, s: str) -> MealId:
        """Create from string."""
        return cls(value=s)


class IdempotencyKey(BaseModel):
    """
    Idempotency key value object.

    Used for duplicate detection in API operations.

    Example:
        >>> key = IdempotencyKey(value="meal_abc123def")
        >>> assert str(key) == "meal_abc123def"
    """

    value: str = Field(..., min_length=1, max_length=100, description="Idempotency key")

    def __str__(self) -> str:
        """String representation."""
        return self.value

    def __repr__(self) -> str:
        """Debug representation."""
        return f"IdempotencyKey('{self.value}')"

    def __hash__(self) -> int:
        """Allow use as dict key."""
        return hash(self.value)

    @classmethod
    def from_string(cls, s: str) -> IdempotencyKey:
        """Create from string."""
        return cls(value=s)
