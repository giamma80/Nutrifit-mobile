"""Product lookup adapters for meal domain.

This module provides adapters for looking up product information from various sources.
Following the port-adapter pattern, these adapters implement the ProductLookupPort interface.
"""

from __future__ import annotations
from typing import Any, List, Optional

from ..model.meal import ProductInfo, NutrientProfile
from ..port import ProductLookupPort


class StubProductLookupAdapter(ProductLookupPort):
    """Stub implementation of product lookup for testing and development.

    Returns predefined product data for common barcodes.
    Future implementations can integrate with OpenFoodFacts, UPC databases, etc.
    """

    def __init__(self) -> None:
        # Predefined product database for testing
        self._products = {
            "8901030789366": ProductInfo(
                barcode="8901030789366",
                name="Chicken Breast (Raw)",
                nutrient_profile=NutrientProfile(
                    calories_per_100g=165.0,
                    protein_per_100g=31.0,
                    carbs_per_100g=0.0,
                    fat_per_100g=3.6,
                    fiber_per_100g=0.0,
                    sugar_per_100g=0.0,
                    sodium_per_100g=74.0,
                ),
            ),
            "1234567890123": ProductInfo(
                barcode="1234567890123",
                name="Basmati Rice (Dry)",
                nutrient_profile=NutrientProfile(
                    calories_per_100g=356.0,
                    protein_per_100g=8.9,
                    carbs_per_100g=78.0,
                    fat_per_100g=0.6,
                    fiber_per_100g=1.8,
                    sugar_per_100g=0.0,
                    sodium_per_100g=2.0,
                ),
            ),
            "9876543210987": ProductInfo(
                barcode="9876543210987",
                name="Greek Yogurt (Plain)",
                nutrient_profile=NutrientProfile(
                    calories_per_100g=97.0,
                    protein_per_100g=9.0,
                    carbs_per_100g=3.6,
                    fat_per_100g=5.0,
                    fiber_per_100g=0.0,
                    sugar_per_100g=3.6,
                    sodium_per_100g=36.0,
                ),
            ),
            "5555666677778": ProductInfo(
                barcode="5555666677778",
                name="Whole Wheat Bread",
                nutrient_profile=NutrientProfile(
                    calories_per_100g=247.0,
                    protein_per_100g=13.0,
                    carbs_per_100g=41.0,
                    fat_per_100g=4.2,
                    fiber_per_100g=7.0,
                    sugar_per_100g=4.0,
                    sodium_per_100g=491.0,
                ),
            ),
        }

    async def lookup_by_barcode(self, barcode: str) -> Optional[ProductInfo]:
        """Look up product information by barcode."""
        return self._products.get(barcode)

    async def search_products(self, query: str, limit: int = 10) -> List[ProductInfo]:
        """Search products by text query."""
        query_lower = query.lower()
        results = []

        for product in self._products.values():
            if query_lower in product.name.lower():
                results.append(product)

        return results[:limit]


class OpenFoodFactsAdapter(ProductLookupPort):
    """OpenFoodFacts API integration for product lookup.

    Reuses the working openfoodfacts.adapter to avoid code duplication.
    """

    def __init__(self) -> None:
        pass

    async def lookup_by_barcode(self, barcode: str) -> Optional[ProductInfo]:
        """Look up product via OpenFoodFacts API using the working adapter."""
        try:
            # Import the working adapter
            from openfoodfacts import adapter

            # Use the working adapter to fetch product data
            dto = await adapter.fetch_product(barcode)

            # Convert DTO to our domain ProductInfo
            nutrient_profile = NutrientProfile(
                calories_per_100g=dto.nutrients.get("calories", 0.0),
                protein_per_100g=dto.nutrients.get("protein", 0.0),
                carbs_per_100g=dto.nutrients.get("carbs", 0.0),
                fat_per_100g=dto.nutrients.get("fat", 0.0),
                fiber_per_100g=dto.nutrients.get("fiber", 0.0),
                sugar_per_100g=dto.nutrients.get("sugar", 0.0),
                sodium_per_100g=dto.nutrients.get("sodium", 0.0),
            )

            return ProductInfo(
                barcode=dto.barcode,
                name=dto.name,
                nutrient_profile=nutrient_profile,
                image_url=dto.image_url,  # This is the key field that was missing!
            )

        except adapter.ProductNotFound:
            return None
        except Exception:
            # Graceful error handling for other exceptions
            return None

    async def search_products(self, query: str, limit: int = 10) -> List[ProductInfo]:
        """Search products via text query - not implemented for now."""
        # For now return empty list, can be implemented later if needed
        return []

    async def __aenter__(self) -> "OpenFoodFactsAdapter":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        # No cleanup needed since we delegate to the working adapter
        pass
