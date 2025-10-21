"""
OpenFoodFacts domain models.

Models for OpenFoodFacts API responses mapped to our domain.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class NutriscoreGrade(str, Enum):
    """Nutriscore grade classification."""

    A = "a"  # Best
    B = "b"
    C = "c"
    D = "d"
    E = "e"  # Worst
    UNKNOWN = "unknown"


class NovaGroup(str, Enum):
    """NOVA food processing classification."""

    GROUP_1 = "1"  # Unprocessed or minimally processed
    GROUP_2 = "2"  # Processed culinary ingredients
    GROUP_3 = "3"  # Processed foods
    GROUP_4 = "4"  # Ultra-processed foods
    UNKNOWN = "unknown"


class OFFNutriments(BaseModel):
    """OpenFoodFacts nutriments (per 100g).

    Example:
        >>> nutriments = OFFNutriments(
        ...     energy_kcal=150.0,
        ...     proteins=3.0,
        ...     carbohydrates=25.0,
        ...     fat=5.0,
        ... )
        >>> assert nutriments.energy_kcal == 150.0
    """

    energy_kcal: Optional[float] = Field(None, ge=0, description="Energy in kcal per 100g")
    proteins: Optional[float] = Field(None, ge=0, description="Protein in g per 100g")
    carbohydrates: Optional[float] = Field(None, ge=0, description="Carbohydrates in g per 100g")
    fat: Optional[float] = Field(None, ge=0, description="Fat in g per 100g")
    fiber: Optional[float] = Field(None, ge=0, description="Fiber in g per 100g")
    sugars: Optional[float] = Field(None, ge=0, description="Sugars in g per 100g")
    sodium: Optional[float] = Field(None, ge=0, description="Sodium in mg per 100g")
    salt: Optional[float] = Field(None, ge=0, description="Salt in g per 100g")

    class Config:
        """Pydantic configuration."""

        frozen = True


class OFFProduct(BaseModel):
    """OpenFoodFacts product response.

    Example:
        >>> product = OFFProduct(
        ...     code="3017620422003",
        ...     product_name="Nutella",
        ...     brands="Ferrero",
        ...     nutriments=OFFNutriments(
        ...         energy_kcal=539.0,
        ...         proteins=6.3,
        ...         carbohydrates=57.5,
        ...         fat=30.9,
        ...     ),
        ... )
        >>> assert product.code == "3017620422003"
        >>> assert product.product_name == "Nutella"
    """

    code: str = Field(..., description="Product barcode")
    product_name: Optional[str] = Field(None, description="Product name")
    brands: Optional[str] = Field(None, description="Brand names")
    categories: Optional[str] = Field(None, description="Product categories")
    quantity: Optional[str] = Field(None, description="Product quantity (e.g., '750g')")
    serving_size: Optional[str] = Field(None, description="Serving size (e.g., '30g')")
    image_url: Optional[str] = Field(None, description="Product image URL")
    nutriments: Optional[OFFNutriments] = Field(None, description="Nutritional values")
    nutriscore_grade: Optional[NutriscoreGrade] = Field(None, description="Nutriscore grade (a-e)")
    nova_group: Optional[NovaGroup] = Field(None, description="NOVA processing group (1-4)")
    ingredients_text: Optional[str] = Field(None, description="Ingredients list")
    allergens: Optional[str] = Field(None, description="Allergens list")

    class Config:
        """Pydantic configuration."""

        frozen = True


class OFFSearchResult(BaseModel):
    """OpenFoodFacts search response.

    Example:
        >>> result = OFFSearchResult(
        ...     status=1,
        ...     product=OFFProduct(
        ...         code="3017620422003",
        ...         product_name="Nutella",
        ...         brands="Ferrero",
        ...     ),
        ... )
        >>> assert result.status == 1
        >>> assert result.product is not None
    """

    status: int = Field(..., description="API status (1=found, 0=not)")
    product: Optional[OFFProduct] = Field(None, description="Product data (if found)")

    class Config:
        """Pydantic configuration."""

        frozen = True

    def is_found(self) -> bool:
        """Check if product was found.

        Returns:
            True if product exists in database
        """
        return self.status == 1 and self.product is not None


class BarcodeDataSource(str, Enum):
    """Source of barcode nutrition data."""

    USDA = "USDA"
    OPENFOODFACTS = "OpenFoodFacts"
    MERGED = "Merged"  # USDA + OpenFoodFacts
    UNKNOWN = "Unknown"


class BarcodeQuality(BaseModel):
    """Quality metrics for barcode data.

    Example:
        >>> quality = BarcodeQuality(
        ...     completeness=0.85,
        ...     source_reliability=0.90,
        ...     data_freshness=0.95,
        ... )
        >>> score = quality.overall_score()
        >>> assert 0.0 <= score <= 1.0
    """

    completeness: float = Field(..., ge=0.0, le=1.0, description="Data completeness (0-1)")
    source_reliability: float = Field(..., ge=0.0, le=1.0, description="Source reliability (0-1)")
    data_freshness: float = Field(..., ge=0.0, le=1.0, description="Data freshness (0-1)")

    def overall_score(self) -> float:
        """Calculate overall quality score.

        Returns:
            Weighted average quality score (0-1)
        """
        return round(
            (self.completeness * 0.4 + self.source_reliability * 0.4 + self.data_freshness * 0.2),
            2,
        )

    class Config:
        """Pydantic configuration."""

        frozen = True
