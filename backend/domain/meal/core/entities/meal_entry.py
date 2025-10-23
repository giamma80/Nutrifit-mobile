"""MealEntry entity - individual food item within a meal."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4


@dataclass
class MealEntry:
    """
    Entity: Single dish in a meal.

    Represents an individual food item (piatto) within a complete meal (pasto).
    Example: "Pasta al pomodoro" is a MealEntry in "Pranzo" Meal.

    Identity: Defined by unique ID (UUID)
    Mutability: Can be modified (quantity, nutrients can change)
    """

    id: UUID
    meal_id: UUID

    # Food identification
    name: str  # Machine-readable label (e.g., "pasta")
    display_name: str  # User-friendly name (e.g., "Pasta al Pomodoro")
    quantity_g: float  # Quantity in grams

    # Macronutrients (denormalized for query performance)
    calories: int
    protein: float  # grams
    carbs: float  # grams
    fat: float  # grams

    # Micronutrients (optional)
    fiber: Optional[float] = None  # grams
    sugar: Optional[float] = None  # grams
    sodium: Optional[float] = None  # milligrams

    # Metadata
    source: str = "MANUAL"  # PHOTO | BARCODE | DESCRIPTION | MANUAL
    confidence: float = 1.0  # 0.0 - 1.0
    category: Optional[str] = None  # vegetables, fruits, meat, etc.
    barcode: Optional[str] = None  # EAN/UPC code
    image_url: Optional[str] = None  # Photo URL

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Validate invariants after initialization."""
        if self.quantity_g <= 0:
            raise ValueError(f"Quantity must be positive, got {self.quantity_g}")

        if self.calories < 0:
            raise ValueError(f"Calories cannot be negative, got {self.calories}")

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0 and 1, got {self.confidence}")

        if self.source not in ["PHOTO", "BARCODE", "DESCRIPTION", "MANUAL"]:
            raise ValueError(f"Invalid source: {self.source}")

        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware (use UTC)")

    def scale_nutrients(self, target_quantity_g: float) -> "MealEntry":
        """
        Create new entry with scaled nutrients to target quantity.

        Useful for scaling a reference entry (e.g., 100g) to actual consumed quantity.

        Args:
            target_quantity_g: Target quantity in grams

        Returns:
            New MealEntry with scaled nutrients

        Raises:
            ValueError: If target_quantity_g is not positive
        """
        if target_quantity_g <= 0:
            raise ValueError(f"Target quantity must be positive, got {target_quantity_g}")

        factor = target_quantity_g / self.quantity_g

        return MealEntry(
            id=uuid4(),  # New entry gets new ID
            meal_id=self.meal_id,
            name=self.name,
            display_name=self.display_name,
            quantity_g=target_quantity_g,
            calories=int(self.calories * factor),
            protein=self.protein * factor,
            carbs=self.carbs * factor,
            fat=self.fat * factor,
            fiber=self.fiber * factor if self.fiber is not None else None,
            sugar=self.sugar * factor if self.sugar is not None else None,
            sodium=self.sodium * factor if self.sodium is not None else None,
            source=self.source,
            confidence=self.confidence,
            category=self.category,
            barcode=self.barcode,
            image_url=self.image_url,
            created_at=self.created_at,
        )

    def update_quantity(self, new_quantity_g: float) -> None:
        """
        Update quantity and scale nutrients accordingly IN PLACE.

        This mutates the existing entry rather than creating a new one.

        Args:
            new_quantity_g: New quantity in grams

        Raises:
            ValueError: If new_quantity_g is not positive
        """
        if new_quantity_g <= 0:
            raise ValueError(f"Quantity must be positive, got {new_quantity_g}")

        factor = new_quantity_g / self.quantity_g

        self.quantity_g = new_quantity_g
        self.calories = int(self.calories * factor)
        self.protein *= factor
        self.carbs *= factor
        self.fat *= factor

        if self.fiber is not None:
            self.fiber *= factor
        if self.sugar is not None:
            self.sugar *= factor
        if self.sodium is not None:
            self.sodium *= factor

    def is_reliable(self) -> bool:
        """
        Check if entry has reliable data (confidence > 0.7).

        Returns:
            True if confidence score indicates reliable data
        """
        return self.confidence > 0.7
