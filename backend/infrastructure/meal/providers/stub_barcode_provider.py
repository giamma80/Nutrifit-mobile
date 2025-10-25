"""Stub barcode provider for testing.

Returns fake barcode products without calling external APIs (OpenFoodFacts, etc.).
Useful for integration/E2E tests.
"""

from typing import Optional

from domain.meal.barcode.entities.barcode_product import BarcodeProduct
from domain.meal.nutrition.entities.nutrient_profile import NutrientProfile


class StubBarcodeProvider:
    """
    Stub implementation of IBarcodeProvider for testing.

    Returns hardcoded product data based on barcode.
    """

    async def lookup_barcode(self, barcode: str) -> Optional[BarcodeProduct]:
        """
        Look up product by barcode.

        Args:
            barcode: EAN/UPC code

        Returns:
            BarcodeProduct with stub data if barcode is recognized, None otherwise
        """
        # Map well-known barcodes to products
        product_map = {
            "8001505005707": {  # Nutella (real barcode)
                "name": "Nutella",
                "brand": "Ferrero",
                "nutrients": NutrientProfile(
                    calories=539.0,
                    protein=6.3,
                    carbs=57.5,
                    fat=30.9,
                    fiber=0.0,
                    sugar=56.3,
                    sodium=40.0,
                    quantity_g=100.0,  # Per 100g
                ),
                "serving_size_g": 100.0,
                "image_url": "https://images.openfoodfacts.org/images/products/800/150/500/5707/front_en.jpg",
            },
            "123456789": {  # Generic test barcode
                "name": "Test Product",
                "brand": "Test Brand",
                "nutrients": NutrientProfile(
                    calories=200.0,
                    protein=10.0,
                    carbs=25.0,
                    fat=5.0,
                    fiber=2.0,
                    sugar=10.0,
                    sodium=100.0,
                    quantity_g=100.0,
                ),
                "serving_size_g": 100.0,
                "image_url": None,
            },
        }

        # Get product data if barcode is known
        product_data = product_map.get(barcode)
        if not product_data:
            return None

        return BarcodeProduct(
            barcode=barcode,
            name=product_data["name"],
            brand=product_data["brand"],
            nutrients=product_data["nutrients"],
            serving_size_g=product_data["serving_size_g"],
            image_url=product_data["image_url"],
        )
