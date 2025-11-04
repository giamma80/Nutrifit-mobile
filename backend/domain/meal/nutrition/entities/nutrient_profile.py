"""NutrientProfile entity - complete nutritional data for a food item."""

from dataclasses import dataclass
from typing import Literal, Optional

NutrientSource = Literal["USDA", "BARCODE_DB", "CATEGORY", "AI_ESTIMATE"]


@dataclass
class NutrientProfile:
    """
    Entity: Complete nutrient profile for a food item.

    Contains both macronutrients and micronutrients with metadata about
    the source and confidence of the data.

    Identity: Not a true entity (no unique ID), but treated as a rich domain object
    that encapsulates nutrient data and business logic.
    """

    # Macronutrients (required)
    calories: int  # kcal
    protein: float  # grams
    carbs: float  # grams
    fat: float  # grams

    # Micronutrients (optional)
    fiber: Optional[float] = None  # grams
    sugar: Optional[float] = None  # grams
    sodium: Optional[float] = None  # milligrams

    # Metadata
    source: NutrientSource = "USDA"
    confidence: float = 0.9  # 0.0 - 1.0
    quantity_g: float = 100.0  # Reference quantity (typically 100g)

    def __post_init__(self) -> None:
        """Validate invariants after initialization."""
        if self.quantity_g <= 0:
            raise ValueError(f"Quantity must be positive, got {self.quantity_g}")

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")

        if self.calories < 0:
            raise ValueError(f"Calories cannot be negative, got {self.calories}")

        if self.protein < 0:
            raise ValueError(f"Protein cannot be negative, got {self.protein}")

        if self.carbs < 0:
            raise ValueError(f"Carbs cannot be negative, got {self.carbs}")

        if self.fat < 0:
            raise ValueError(f"Fat cannot be negative, got {self.fat}")

    def scale_to_quantity(self, target_g: float) -> "NutrientProfile":
        """
        Scale nutrients to target quantity.

        Useful for converting from reference quantity (typically 100g)
        to actual consumed quantity.

        Args:
            target_g: Target quantity in grams

        Returns:
            New NutrientProfile scaled to target quantity

        Raises:
            ValueError: If target_g is not positive

        Example:
            >>> profile = NutrientProfile(calories=200, protein=10, carbs=30, fat=5, quantity_g=100)
            >>> scaled = profile.scale_to_quantity(150)  # Scale to 150g
            >>> scaled.calories
            300
        """
        if target_g <= 0:
            raise ValueError(f"Target quantity must be positive, got {target_g}")

        factor = target_g / self.quantity_g

        return NutrientProfile(
            calories=int(self.calories * factor),
            protein=self.protein * factor,
            carbs=self.carbs * factor,
            fat=self.fat * factor,
            fiber=self.fiber * factor if self.fiber is not None else None,
            sugar=self.sugar * factor if self.sugar is not None else None,
            sodium=self.sodium * factor if self.sodium is not None else None,
            source=self.source,
            confidence=self.confidence,
            quantity_g=target_g,
        )

    def calories_from_macros(self) -> int:
        """
        Calculate calories from macronutrients using 4-4-9 rule.

        The Atwater system:
        - Protein: 4 kcal/g
        - Carbs: 4 kcal/g
        - Fat: 9 kcal/g

        Returns:
            Calculated calories from macros

        Example:
            >>> profile = NutrientProfile(
            ...     calories=200,  # Declared calories
            ...     protein=10,     # 10g * 4 = 40 kcal
            ...     carbs=30,       # 30g * 4 = 120 kcal
            ...     fat=5           # 5g * 9 = 45 kcal
            ... )
            >>> profile.calories_from_macros()
            205  # 40 + 120 + 45
        """
        return int(self.protein * 4 + self.carbs * 4 + self.fat * 9)

    def is_high_quality(self) -> bool:
        """
        Check if nutritional data is high quality.

        High quality means:
        - Source is USDA or barcode database (not estimated)
        - Confidence score is above 0.8

        Returns:
            True if data is from reliable source with high confidence

        Example:
            >>> profile = NutrientProfile(
            ...     calories=200, protein=10, carbs=30, fat=5,
            ...     source="USDA", confidence=0.95
            ... )
            >>> profile.is_high_quality()
            True
        """
        return self.source in ["USDA", "BARCODE_DB"] and self.confidence > 0.8

    def macro_distribution(self) -> dict[str, float]:
        """
        Calculate macronutrient distribution as percentages.

        Returns percentage of calories from each macronutrient.

        Returns:
            Dict with protein_pct, carbs_pct, fat_pct

        Example:
            >>> profile = NutrientProfile(
            ...     calories=200,
            ...     protein=10,  # 40 kcal (20%)
            ...     carbs=30,    # 120 kcal (60%)
            ...     fat=5        # 45 kcal (20%)
            ... )
            >>> dist = profile.macro_distribution()
            >>> dist["protein_pct"]
            19.5...  # ~20%
        """
        total_cals = self.calories_from_macros()

        if total_cals == 0:
            return {"protein_pct": 0.0, "carbs_pct": 0.0, "fat_pct": 0.0}

        return {
            "protein_pct": (self.protein * 4 / total_cals) * 100,
            "carbs_pct": (self.carbs * 4 / total_cals) * 100,
            "fat_pct": (self.fat * 9 / total_cals) * 100,
        }
