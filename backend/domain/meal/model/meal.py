"""Meal domain model - aggregate root and value objects.

Core business entities for meal management following DDD principles.
Immutable domain model with rich behavior and invariants.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


# Value Objects


@dataclass(frozen=True, slots=True)
class MealId:
    """Meal unique identifier."""

    value: str

    @classmethod
    def generate(cls) -> MealId:
        """Generate new unique meal ID."""
        return cls(str(uuid.uuid4()))

    @classmethod
    def from_string(cls, value: str) -> MealId:
        """Create from string value."""
        if not value or not isinstance(value, str):
            raise ValueError("MealId must be non-empty string")
        return cls(value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class UserId:
    """User identifier."""

    value: str

    @classmethod
    def from_string(cls, value: str) -> UserId:
        """Create from string value."""
        if not value or not isinstance(value, str):
            raise ValueError("UserId must be non-empty string")
        return cls(value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class NutrientProfile:
    """Nutritional profile per 100g of food."""

    calories_per_100g: Optional[float] = None
    protein_per_100g: Optional[float] = None
    carbs_per_100g: Optional[float] = None
    fat_per_100g: Optional[float] = None
    fiber_per_100g: Optional[float] = None
    sugar_per_100g: Optional[float] = None
    sodium_per_100g: Optional[float] = None

    def scale_to_quantity(self, quantity_g: float) -> ScaledNutrients:
        """Scale nutrients to actual quantity consumed."""
        if quantity_g <= 0:
            raise ValueError("Quantity must be positive")

        factor = quantity_g / 100.0

        return ScaledNutrients(
            calories=(
                int(round(self.calories_per_100g * factor))
                if self.calories_per_100g is not None
                else None
            ),
            protein=(
                round(self.protein_per_100g * factor, 2)
                if self.protein_per_100g is not None
                else None
            ),
            carbs=(
                round(self.carbs_per_100g * factor, 2) if self.carbs_per_100g is not None else None
            ),
            fat=(round(self.fat_per_100g * factor, 2) if self.fat_per_100g is not None else None),
            fiber=(
                round(self.fiber_per_100g * factor, 2) if self.fiber_per_100g is not None else None
            ),
            sugar=(
                round(self.sugar_per_100g * factor, 2) if self.sugar_per_100g is not None else None
            ),
            sodium=(
                round(self.sodium_per_100g * factor, 2)
                if self.sodium_per_100g is not None
                else None
            ),
        )

    def has_nutrients(self) -> bool:
        """Check if profile contains any nutritional data."""
        return any(
            [
                self.calories_per_100g is not None,
                self.protein_per_100g is not None,
                self.carbs_per_100g is not None,
                self.fat_per_100g is not None,
                self.fiber_per_100g is not None,
                self.sugar_per_100g is not None,
                self.sodium_per_100g is not None,
            ]
        )


@dataclass(frozen=True, slots=True)
class ScaledNutrients:
    """Nutrients scaled to actual consumed quantity."""

    calories: Optional[int] = None
    protein: Optional[float] = None
    carbs: Optional[float] = None
    fat: Optional[float] = None
    fiber: Optional[float] = None
    sugar: Optional[float] = None
    sodium: Optional[float] = None

    def total_calories(self) -> Optional[int]:
        """Get total calories for this portion."""
        return self.calories


@dataclass(frozen=True, slots=True)
class ProductInfo:
    """External product information from barcode lookup."""

    barcode: str
    name: str
    nutrient_profile: NutrientProfile

    def enrich_meal_with_quantity(self, quantity_g: float) -> ScaledNutrients:
        """Get scaled nutrients for specific quantity."""
        return self.nutrient_profile.scale_to_quantity(quantity_g)


# Aggregate Root


@dataclass(frozen=True, slots=True)
class Meal:
    """Meal aggregate root - core entity for meal management.

    Immutable entity following DDD principles with rich domain behavior.
    Contains meal information and nutritional data with business invariants.
    """

    id: MealId
    user_id: UserId
    name: str
    quantity_g: float
    timestamp: datetime
    nutrients: Optional[ScaledNutrients] = None
    barcode: Optional[str] = None
    idempotency_key: Optional[str] = None
    nutrient_snapshot_json: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate business invariants."""
        if not self.name.strip():
            raise ValueError("Meal name cannot be empty")
        if self.quantity_g <= 0:
            raise ValueError("Meal quantity must be positive")

    def update_nutrients(self, nutrients: ScaledNutrients) -> Meal:
        """Create new meal with updated nutritional information."""
        import json

        # Create nutrient snapshot for compatibility
        snapshot = {
            "calories": nutrients.calories,
            "protein": nutrients.protein,
            "carbs": nutrients.carbs,
            "fat": nutrients.fat,
            "fiber": nutrients.fiber,
            "sugar": nutrients.sugar,
            "sodium": nutrients.sodium,
        }

        return Meal(
            id=self.id,
            user_id=self.user_id,
            name=self.name,
            quantity_g=self.quantity_g,
            timestamp=self.timestamp,
            nutrients=nutrients,
            barcode=self.barcode,
            idempotency_key=self.idempotency_key,
            nutrient_snapshot_json=json.dumps(snapshot, sort_keys=True),
        )

    def change_quantity(self, new_quantity_g: float) -> Meal:
        """Create new meal with updated quantity."""
        if new_quantity_g <= 0:
            raise ValueError("New quantity must be positive")

        return Meal(
            id=self.id,
            user_id=self.user_id,
            name=self.name,
            quantity_g=new_quantity_g,
            timestamp=self.timestamp,
            nutrients=self.nutrients,
            barcode=self.barcode,
            idempotency_key=self.idempotency_key,
            nutrient_snapshot_json=self.nutrient_snapshot_json,
        )

    def update_basic_info(
        self,
        name: Optional[str] = None,
        timestamp: Optional[datetime] = None,
        barcode: Optional[str] = None,
    ) -> Meal:
        """Create new meal with updated basic information."""
        new_name = name if name is not None else self.name
        new_timestamp = timestamp if timestamp is not None else self.timestamp
        new_barcode = barcode if barcode is not None else self.barcode

        if new_name and not new_name.strip():
            raise ValueError("Meal name cannot be empty")

        return Meal(
            id=self.id,
            user_id=self.user_id,
            name=new_name,
            quantity_g=self.quantity_g,
            timestamp=new_timestamp,
            nutrients=self.nutrients,
            barcode=new_barcode,
            idempotency_key=self.idempotency_key,
            nutrient_snapshot_json=self.nutrient_snapshot_json,
        )

    def total_calories(self) -> Optional[int]:
        """Get total calories for this meal."""
        return self.nutrients.total_calories() if self.nutrients else None

    def has_nutritional_data(self) -> bool:
        """Check if meal has nutritional information."""
        return self.nutrients is not None

    def has_barcode(self) -> bool:
        """Check if meal has barcode information."""
        return self.barcode is not None and self.barcode.strip() != ""

    def should_recalculate_nutrients(
        self,
        new_quantity_g: Optional[float] = None,
        new_barcode: Optional[str] = None,
    ) -> bool:
        """Determine if nutrients should be recalculated based on changes."""
        quantity_changed = new_quantity_g is not None and new_quantity_g != self.quantity_g
        barcode_changed = new_barcode is not None and new_barcode != self.barcode

        return quantity_changed or barcode_changed


__all__ = [
    "MealId",
    "UserId",
    "NutrientProfile",
    "ScaledNutrients",
    "ProductInfo",
    "Meal",
]
