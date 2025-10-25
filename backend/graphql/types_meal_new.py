"""GraphQL types for new meal domain (Clean Architecture refactored).

These types support the CQRS pattern with atomic queries for testing
individual capabilities (recognition, nutrition, barcode) in isolation.
"""

from __future__ import annotations

from typing import Optional, List
import strawberry


__all__ = [
    # Output types
    "RecognizedFood",
    "FoodRecognitionResult",
    "NutrientProfile",
    "BarcodeProduct",
    # Input types
    "RecognizeFoodInput",
    "EnrichNutrientsInput",
    "SearchFoodByBarcodeInput",
]


# ============================================
# ATOMIC QUERY TYPES (P5.2)
# ============================================


@strawberry.type
class RecognizedFood:
    """Food item recognized from photo or text analysis."""

    label: str
    display_name: str
    quantity_g: float
    confidence: float

    def is_reliable(self) -> bool:
        """Check if recognition confidence is reliable (>= 0.7)."""
        return self.confidence >= 0.7


@strawberry.type
class FoodRecognitionResult:
    """Result of food recognition from photo or text.

    Atomic query result for testing IVisionProvider capability.
    """

    items: List[RecognizedFood]
    average_confidence: float

    def item_count(self) -> int:
        """Number of recognized items."""
        return len(self.items)

    def reliable_items(self) -> List[RecognizedFood]:
        """Get only reliable items (confidence >= 0.7)."""
        return [item for item in self.items if item.is_reliable()]


@strawberry.type
class NutrientProfile:
    """Complete nutrient profile for 100g of food.

    Atomic query result for testing INutritionProvider capability.
    """

    calories: float
    protein: float
    carbs: float
    fat: float
    fiber: Optional[float] = None
    sugar: Optional[float] = None
    sodium: Optional[float] = None
    quantity_g: float = 100.0

    def calories_from_macros(self) -> float:
        """Calculate calories from macronutrients (4-4-9 rule)."""
        return (self.protein * 4) + (self.carbs * 4) + (self.fat * 9)

    def is_high_quality(self) -> bool:
        """Check if nutrient data is complete and high quality."""
        return all(
            [
                self.calories > 0,
                self.protein >= 0,
                self.carbs >= 0,
                self.fat >= 0,
                self.fiber is not None,
                self.sugar is not None,
                self.sodium is not None,
            ]
        )


@strawberry.type
class BarcodeProduct:
    """Product information from barcode lookup.

    Atomic query result for testing IBarcodeProvider capability.
    """

    barcode: str
    name: str
    brand: Optional[str] = None
    nutrients: Optional[NutrientProfile] = None
    serving_size_g: Optional[float] = None
    image_url: Optional[str] = None

    def has_image(self) -> bool:
        """Check if product has image."""
        return self.image_url is not None

    def has_brand(self) -> bool:
        """Check if product has brand info."""
        return self.brand is not None and len(self.brand) > 0

    def display_name(self) -> str:
        """Get display name with brand if available."""
        if self.has_brand():
            return f"{self.brand} {self.name}"
        return self.name


# ============================================
# INPUT TYPES
# ============================================


@strawberry.input
class RecognizeFoodInput:
    """Input for recognizeFood atomic query."""

    photo_url: Optional[str] = None
    text: Optional[str] = None
    dish_hint: Optional[str] = None


@strawberry.input
class EnrichNutrientsInput:
    """Input for enrichNutrients atomic query."""

    label: str
    quantity_g: float


@strawberry.input
class SearchFoodByBarcodeInput:
    """Input for searchFoodByBarcode atomic query."""

    barcode: str
