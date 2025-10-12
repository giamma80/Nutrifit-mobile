"""Product lookup adapter - bridges domain to external product databases.

Provides product information lookup by barcode and text search,
with stub implementation for testing and future extension to real APIs.
"""

from __future__ import annotations

from typing import List, Optional

from domain.meal.model import NutrientProfile, ProductInfo
from domain.meal.port import ProductLookupPort


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

    async def search_products(
        self, query: str, limit: int = 10
    ) -> List[ProductInfo]:
        """Search products by text query."""
        query_lower = query.lower()
        results = []

        for product in self._products.values():
            if query_lower in product.name.lower():
                results.append(product)

        return results[:limit]


class OpenFoodFactsAdapter(ProductLookupPort):
    """Future implementation for OpenFoodFacts API integration.

    Placeholder for real external API integration.
    """

    def __init__(self, api_key: Optional[str] = None) -> None:
        self._api_key = api_key
        # TODO: Initialize HTTP client, rate limiting, etc.

    async def lookup_by_barcode(self, barcode: str) -> Optional[ProductInfo]:
        """Look up product via OpenFoodFacts API."""
        # TODO: Implement actual API call
        # - HTTP request to openfoodfacts.org/api/v0/product/{barcode}.json
        # - Parse response and map to ProductInfo
        # - Handle rate limiting and errors
        # - Cache responses
        raise NotImplementedError(
            "OpenFoodFacts integration not yet implemented"
        )

    async def search_products(
        self, query: str, limit: int = 10
    ) -> List[ProductInfo]:
        """Search products via OpenFoodFacts API."""
        # TODO: Implement actual API search
        # - HTTP request to search endpoint
        # - Parse results and map to List[ProductInfo]
        # - Handle pagination
        raise NotImplementedError("OpenFoodFacts search not yet implemented")
