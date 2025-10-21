"""
Nutrition domain models.

Core domain models for nutrition data and enrichment.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict


class NutrientSource(str, Enum):
    """
    Source of nutrient data.

    Indicates origin and reliability of nutritional information.
    """

    USDA = "USDA"  # High quality, verified
    BARCODE_DB = "BARCODE_DB"  # OpenFoodFacts, high quality
    CATEGORY_PROFILE = "CATEGORY_PROFILE"  # Fallback, medium quality
    ESTIMATED = "ESTIMATED"  # Category-based estimate
    AI_ESTIMATE = "AI_ESTIMATE"  # AI-generated, low quality
    MANUAL = "MANUAL"  # User-entered


class NutrientProfile(BaseModel):
    """
    Complete nutrient profile for a food item.

    Represents nutritional information per reference quantity (usually 100g).
    Immutable value object with scaling capability.

    Attributes:
        calories: Energy in kcal
        protein: Protein in grams
        carbs: Carbohydrates in grams
        fat: Total fat in grams
        fiber: Dietary fiber in grams (optional)
        sugar: Total sugars in grams (optional)
        sodium: Sodium in mg (optional)
        source: Data source (USDA, barcode, etc.)
        confidence: Reliability score (0.0 - 1.0)
        quantity_g: Reference quantity (usually 100g)

    Example:
        >>> profile = NutrientProfile(
        ...     calories=165,
        ...     protein=31.0,
        ...     carbs=0.0,
        ...     fat=3.6,
        ...     source=NutrientSource.USDA,
        ...     confidence=0.95,
        ...     quantity_g=100.0,
        ... )
        >>> scaled = profile.scale_to_quantity(150.0)
        >>> assert scaled.calories == 248  # 165 * 1.5
        >>> assert scaled.quantity_g == 150.0
    """

    model_config = ConfigDict(frozen=True, use_enum_values=True)

    # Required macronutrients
    calories: int = Field(..., ge=0, description="Energy in kcal")
    protein: float = Field(..., ge=0, description="Protein in g")
    carbs: float = Field(..., ge=0, description="Carbohydrates in g")
    fat: float = Field(..., ge=0, description="Total fat in g")

    # Optional micronutrients
    fiber: Optional[float] = Field(None, ge=0, description="Fiber in g")
    sugar: Optional[float] = Field(None, ge=0, description="Sugar in g")
    sodium: Optional[float] = Field(None, ge=0, description="Sodium in mg")

    # Metadata
    source: NutrientSource = Field(NutrientSource.USDA, description="Data source")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Reliability (0-1)")
    quantity_g: float = Field(100.0, gt=0, description="Reference quantity in grams")

    @field_validator("confidence")
    @classmethod
    def round_confidence(cls, v: float) -> float:
        """Round confidence to 2 decimal places."""
        return round(v, 2)

    def scale_to_quantity(self, target_g: float) -> NutrientProfile:
        """
        Scale nutrients to target quantity.

        Creates a new NutrientProfile scaled proportionally.

        Args:
            target_g: Target quantity in grams

        Returns:
            New NutrientProfile scaled to target_g

        Example:
            >>> profile = NutrientProfile(
            ...     calories=100, protein=20.0, carbs=10.0, fat=5.0,
            ...     source=NutrientSource.USDA, confidence=0.9,
            ...     quantity_g=100.0
            ... )
            >>> scaled = profile.scale_to_quantity(250.0)
            >>> assert scaled.calories == 250
            >>> assert scaled.protein == 50.0
        """
        if target_g <= 0:
            raise ValueError(f"Target quantity must be positive: {target_g}")

        factor = target_g / self.quantity_g

        return NutrientProfile(
            calories=int(self.calories * factor),
            protein=round(self.protein * factor, 1),
            carbs=round(self.carbs * factor, 1),
            fat=round(self.fat * factor, 1),
            fiber=round(self.fiber * factor, 1) if self.fiber else None,
            sugar=round(self.sugar * factor, 1) if self.sugar else None,
            sodium=round(self.sodium * factor, 1) if self.sodium else None,
            source=self.source,
            confidence=self.confidence,
            quantity_g=target_g,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage/serialization."""
        return self.model_dump()
