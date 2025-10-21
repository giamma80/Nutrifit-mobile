"""
Domain models for meal persistence.

These are the core domain models representing meal entries in the system.
Following Pydantic for validation, immutability, and type safety.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, validator


class MealEntry(BaseModel):
    """
    Domain model for a meal entry (persistent storage).

    Represents a single food item logged by a user.
    Denormalized with nutrients for query performance.

    Attributes:
        user_id: User who logged this meal
        name: Display name (e.g., "Pizza Margherita")
        quantity_g: Quantity in grams
        timestamp: When meal was consumed (user-provided)
        source: Input method (PHOTO | BARCODE | DESCRIPTION | MANUAL)

        # Denormalized nutrients (for query performance)
        calories: Energy in kcal
        protein: Protein in grams
        carbs: Carbohydrates in grams
        fat: Total fat in grams
        fiber: Dietary fiber in grams (optional)
        sugar: Total sugars in grams (optional)
        sodium: Sodium in mg (optional)

        # Optional metadata
        id: MongoDB ObjectId (set by repository)
        barcode: Product barcode if applicable
        image_url: Photo URL if from photo analysis
        analysis_id: Link to temporary analysis
        idempotency_key: Hash for duplicate detection
        created_at: Server timestamp

    Example:
        >>> meal = MealEntry(
        ...     user_id="user_123",
        ...     name="Grilled Chicken",
        ...     quantity_g=150.0,
        ...     timestamp=datetime.now(timezone.utc),
        ...     source="PHOTO",
        ...     calories=248,
        ...     protein=46.5,
        ...     carbs=0.0,
        ...     fat=5.4,
        ... )
        >>> assert meal.calories == 248
    """

    # Required fields
    user_id: str = Field(..., min_length=1, description="User identifier")
    name: str = Field(..., min_length=1, max_length=200, description="Food name")
    quantity_g: float = Field(..., gt=0, description="Quantity in grams")
    timestamp: datetime = Field(..., description="When meal was consumed")
    source: str = Field(..., pattern="^(PHOTO|BARCODE|DESCRIPTION|MANUAL)$")

    # Macronutrients (denormalized)
    calories: Optional[int] = Field(default=None, ge=0, description="Energy in kcal")
    protein: Optional[float] = Field(default=None, ge=0, description="Protein in g")
    carbs: Optional[float] = Field(default=None, ge=0, description="Carbohydrates in g")
    fat: Optional[float] = Field(default=None, ge=0, description="Fat in g")

    # Micronutrients (optional, denormalized)
    fiber: Optional[float] = Field(default=None, ge=0, description="Fiber in g")
    sugar: Optional[float] = Field(default=None, ge=0, description="Sugar in g")
    sodium: Optional[float] = Field(default=None, ge=0, description="Sodium in mg")

    # Metadata
    id: Optional[str] = Field(default=None, description="MongoDB ObjectId")
    barcode: Optional[str] = Field(
        default=None, pattern=r"^\d{8,13}$", description="Product barcode"
    )
    image_url: Optional[str] = Field(default=None, description="Photo URL")
    analysis_id: Optional[str] = Field(default=None, description="Analysis reference")
    idempotency_key: Optional[str] = Field(default=None, description="Duplicate detection key")
    created_at: Optional[datetime] = Field(default=None, description="Server creation time")

    @validator("name")
    def name_not_empty(cls, v: str) -> str:
        """Ensure name is not just whitespace."""
        if not v.strip():
            raise ValueError("Meal name cannot be empty or whitespace")
        return v.strip()

    @validator("timestamp", "created_at", pre=True)
    def ensure_utc(cls, v: Optional[datetime]) -> Optional[datetime]:
        """Ensure all timestamps are UTC timezone-aware."""
        if v is None:
            return None

        if v.tzinfo is None:
            # Naive datetime → assume UTC
            return v.replace(tzinfo=timezone.utc)

        return v

    @validator("created_at", always=True)
    def set_created_at(cls, v: Optional[datetime]) -> datetime:
        """Auto-set created_at if not provided."""
        if v is None:
            return datetime.now(timezone.utc)
        return v

    class Config:
        """Pydantic configuration."""

        validate_assignment = True
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
