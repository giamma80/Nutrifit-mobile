"""
USDA domain models for nutrition enrichment.

These models represent USDA FoodData Central API responses
mapped to our domain.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class USDADataType(str, Enum):
    """USDA food database types."""

    BRANDED = "Branded"
    SR_LEGACY = "SR Legacy"
    SURVEY = "Survey (FNDDS)"
    FOUNDATION = "Foundation"


class USDANutrient(BaseModel):
    """Single nutrient from USDA response.

    Example:
        >>> nutrient = USDANutrient(
        ...     number="208",
        ...     name="Energy",
        ...     amount=150.0,
        ...     unit="kcal",
        ... )
        >>> assert nutrient.amount == 150.0
    """

    number: str = Field(..., description="USDA nutrient number")
    name: str = Field(..., description="Nutrient name")
    amount: float = Field(..., description="Amount per 100g")
    unit: str = Field(..., description="Unit of measurement")

    class Config:
        """Pydantic configuration."""

        frozen = True


class USDAFoodItem(BaseModel):
    """USDA food item response.

    Example:
        >>> food = USDAFoodItem(
        ...     fdc_id="123456",
        ...     description="Apple, raw",
        ...     data_type=USDADataType.SR_LEGACY,
        ...     nutrients=[
        ...         USDANutrient(
        ...             number="208",
        ...             name="Energy",
        ...             amount=52.0,
        ...             unit="kcal",
        ...         )
        ...     ],
        ... )
        >>> assert food.fdc_id == "123456"
    """

    fdc_id: str = Field(..., description="FoodData Central ID")
    description: str = Field(..., description="Food description")
    data_type: USDADataType = Field(..., description="Database type")
    nutrients: list[USDANutrient] = Field(default_factory=list, description="Nutrient list")
    brand_owner: Optional[str] = Field(None, description="Brand name (branded foods)")
    gtin_upc: Optional[str] = Field(None, description="Barcode (branded foods)")

    class Config:
        """Pydantic configuration."""

        frozen = True


class USDASearchResult(BaseModel):
    """USDA search API response.

    Example:
        >>> result = USDASearchResult(
        ...     total_hits=1,
        ...     current_page=1,
        ...     total_pages=1,
        ...     foods=[
        ...         USDAFoodItem(
        ...             fdc_id="123",
        ...             description="Apple",
        ...             data_type=USDADataType.SR_LEGACY,
        ...             nutrients=[],
        ...         )
        ...     ],
        ... )
        >>> assert result.total_hits == 1
    """

    total_hits: int = Field(..., ge=0, description="Total results")
    current_page: int = Field(..., ge=1, description="Current page")
    total_pages: int = Field(..., ge=0, description="Total pages")
    foods: list[USDAFoodItem] = Field(default_factory=list, description="Food items")

    class Config:
        """Pydantic configuration."""

        frozen = True


class USDACacheEntry(BaseModel):
    """Cached USDA data with TTL.

    Example:
        >>> from datetime import datetime, timedelta
        >>> entry = USDACacheEntry(
        ...     key="barcode:123456789",
        ...     food_item=USDAFoodItem(
        ...         fdc_id="123",
        ...         description="Apple",
        ...         data_type=USDADataType.SR_LEGACY,
        ...         nutrients=[],
        ...     ),
        ...     expires_at=datetime.now() + timedelta(days=7),
        ... )
        >>> assert not entry.is_expired()
    """

    key: str = Field(..., description="Cache key")
    food_item: USDAFoodItem = Field(..., description="Cached data")
    expires_at: float = Field(..., description="Unix timestamp expiry")

    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        import time

        return time.time() > self.expires_at

    class Config:
        """Pydantic configuration."""

        frozen = True


class FoodCategory(str, Enum):
    """Food category for fallback profiles."""

    FRUIT = "fruit"
    VEGETABLE = "vegetable"
    PROTEIN = "protein"
    GRAIN = "grain"
    DAIRY = "dairy"
    FAT = "fat"
    BEVERAGE = "beverage"
    SNACK = "snack"
    DESSERT = "dessert"
    UNKNOWN = "unknown"


class CategoryProfile(BaseModel):
    """Fallback nutrient profile by category.

    Used when USDA lookup fails.

    Example:
        >>> profile = CategoryProfile(
        ...     category=FoodCategory.FRUIT,
        ...     calories_per_100g=52.0,
        ...     protein_per_100g=0.3,
        ...     carbs_per_100g=14.0,
        ...     fat_per_100g=0.2,
        ... )
        >>> assert profile.category == FoodCategory.FRUIT
    """

    category: FoodCategory = Field(..., description="Food category")
    calories_per_100g: float = Field(..., ge=0, description="Average calories")
    protein_per_100g: float = Field(..., ge=0, description="Average protein")
    carbs_per_100g: float = Field(..., ge=0, description="Average carbs")
    fat_per_100g: float = Field(..., ge=0, description="Average fat")
    fiber_per_100g: Optional[float] = Field(None, ge=0, description="Average fiber")
    sugar_per_100g: Optional[float] = Field(None, ge=0, description="Average sugar")
    sodium_per_100g: Optional[float] = Field(None, ge=0, description="Average sodium (mg)")

    class Config:
        """Pydantic configuration."""

        frozen = True
