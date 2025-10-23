"""Barcode product entity.

Represents a food product identified by barcode (EAN/UPC) from
barcode databases like OpenFoodFacts.
"""

from dataclasses import dataclass
from typing import Optional

from domain.meal.nutrition.entities.nutrient_profile import NutrientProfile


@dataclass(frozen=True)
class BarcodeProduct:
    """
    Product identified by barcode scan.

    This entity represents a packaged food product found in barcode
    databases (OpenFoodFacts, UPC databases, etc.).

    Attributes:
        barcode: EAN/UPC code (e.g., "8001505005707")
        name: Product name (e.g., "Mulino Bianco Galletti")
        brand: Brand name (e.g., "Mulino Bianco")
        nutrients: Complete nutritional profile
        image_url: Product image URL (optional)
        serving_size_g: Standard serving size in grams (optional)

    Example:
        >>> product = BarcodeProduct(
        ...     barcode="8001505005707",
        ...     name="Galletti Biscuits",
        ...     brand="Mulino Bianco",
        ...     nutrients=NutrientProfile(...),
        ...     image_url="https://images.openfoodfacts.org/...",
        ...     serving_size_g=25.0
        ... )
        >>> print(f"{product.brand} - {product.name}")
        Mulino Bianco - Galletti Biscuits
    """

    barcode: str
    name: str
    brand: Optional[str]
    nutrients: NutrientProfile
    image_url: Optional[str] = None
    serving_size_g: Optional[float] = None

    def __post_init__(self) -> None:
        """Validate barcode product invariants."""
        if not self.barcode or not self.barcode.strip():
            raise ValueError("Barcode cannot be empty")

        # Barcodes should be alphanumeric (EAN-13, UPC-A, etc.)
        if not self.barcode.replace("-", "").replace(" ", "").isalnum():
            raise ValueError("Barcode must be alphanumeric")

        if not self.name or not self.name.strip():
            raise ValueError("Product name cannot be empty")

        if self.serving_size_g is not None and self.serving_size_g <= 0:
            raise ValueError("Serving size must be positive")

    def has_image(self) -> bool:
        """Check if product has an image URL.

        Returns:
            True if image_url is set and non-empty

        Example:
            >>> product = BarcodeProduct(...)
            >>> if product.has_image():
            ...     display_image(product.image_url)
        """
        return self.image_url is not None and len(self.image_url.strip()) > 0

    def has_brand(self) -> bool:
        """Check if product has brand information.

        Returns:
            True if brand is set and non-empty

        Example:
            >>> product = BarcodeProduct(...)
            >>> name = (
            ...     f"{product.brand} - {product.name}"
            ...     if product.has_brand()
            ...     else product.name
            ... )
        """
        return self.brand is not None and len(self.brand.strip()) > 0

    def display_name(self) -> str:
        """Get user-friendly display name.

        Returns:
            Brand + name if brand exists, otherwise just name

        Example:
            >>> product = BarcodeProduct(barcode="123", name="Biscuits", brand="Mulino Bianco", ...)
            >>> product.display_name()
            'Mulino Bianco - Biscuits'

            >>> product2 = BarcodeProduct(barcode="456", name="Generic Crackers", brand=None, ...)
            >>> product2.display_name()
            'Generic Crackers'
        """
        if self.has_brand():
            return f"{self.brand} - {self.name}"
        return self.name

    def scale_nutrients(self, quantity_g: float) -> NutrientProfile:
        """Scale nutrients to specific quantity.

        Args:
            quantity_g: Target quantity in grams

        Returns:
            Scaled nutrient profile

        Raises:
            ValueError: If quantity is not positive

        Example:
            >>> product = BarcodeProduct(...)  # nutrients per 100g
            >>> nutrients_for_50g = product.scale_nutrients(50.0)
        """
        if quantity_g <= 0:
            raise ValueError("Quantity must be positive")

        return self.nutrients.scale_to_quantity(quantity_g)

    def is_high_quality(self) -> bool:
        """Check if product has high-quality data.

        Returns:
            True if nutrients are from barcode database with high confidence

        Example:
            >>> product = BarcodeProduct(...)
            >>> if product.is_high_quality():
            ...     print("Accurate nutritional data available")
        """
        return self.nutrients.is_high_quality()
