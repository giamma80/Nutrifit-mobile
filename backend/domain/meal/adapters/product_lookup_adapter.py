"""Product lookup adapter - bridges domain to external product databases.

Provides product information lookup by barcode and text search,
with stub implementation for testing and future extension to real APIs.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

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

    Provides real product data from the OpenFoodFacts database.
    """

    def __init__(self, base_url: str = "https://world.openfoodfacts.org") -> None:
        self._base_url = base_url
        self._session = None
        self._user_agent = "Nutrifit-1.0"

    async def _get_session(self) -> Optional[Any]:
        """Lazy initialization of HTTP session."""
        if self._session is None:
            try:
                import aiohttp

                self._session = aiohttp.ClientSession(
                    headers={"User-Agent": self._user_agent},
                    timeout=aiohttp.ClientTimeout(total=10.0),
                )
            except ImportError:
                # Graceful fallback if aiohttp not available
                return None
        return self._session

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        """Safely convert value to float."""
        if value is None or value == "":
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def _parse_product_data(self, data: Dict[str, Any]) -> Optional[ProductInfo]:
        """Parse OpenFoodFacts product data to ProductInfo."""
        try:
            product = data.get("product", {})

            # Basic product info
            barcode = product.get("code", "")
            name = (
                product.get("product_name")
                or product.get("product_name_en")
                or product.get("generic_name")
                or "Unknown Product"
            )

            # Nutrition data (per 100g)
            nutrients = product.get("nutriments", {})

            nutrient_profile = NutrientProfile(
                calories_per_100g=self._safe_float(
                    nutrients.get("energy-kcal_100g")
                    or
                    # Convert kJ to kcal
                    nutrients.get("energy_100g", 0) / 4.184
                ),
                protein_per_100g=self._safe_float(nutrients.get("proteins_100g")),
                carbs_per_100g=self._safe_float(nutrients.get("carbohydrates_100g")),
                fat_per_100g=self._safe_float(nutrients.get("fat_100g")),
                fiber_per_100g=self._safe_float(nutrients.get("fiber_100g")),
                sugar_per_100g=self._safe_float(nutrients.get("sugars_100g")),
                sodium_per_100g=self._safe_float(
                    nutrients.get("sodium_100g")
                    or
                    # Convert salt to sodium
                    (self._safe_float(nutrients.get("salt_100g")) / 2.54)
                ),
            )

            return ProductInfo(
                barcode=barcode,
                name=name,
                nutrient_profile=nutrient_profile,
            )

        except Exception:
            return None

    async def lookup_by_barcode(self, barcode: str) -> Optional[ProductInfo]:
        """Look up product via OpenFoodFacts API."""
        session = await self._get_session()
        if not session:
            return None

        try:
            url = f"{self._base_url}/api/v0/product/{barcode}.json"
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == 1:  # Product found
                        return self._parse_product_data(data)
                return None

        except Exception:
            # Graceful error handling - return None for network/parsing errors
            return None

    async def search_products(self, query: str, limit: int = 10) -> List[ProductInfo]:
        """Search products via OpenFoodFacts API."""
        session = await self._get_session()
        if not session:
            return []

        try:
            # Use the search API with JSON format
            url = f"{self._base_url}/cgi/search.pl"
            params = {
                "search_terms": query,
                "search_simple": 1,
                "action": "process",
                "json": 1,
                "page_size": min(limit, 50),  # API limit
            }

            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    products = data.get("products", [])

                    results = []
                    for product_data in products:
                        # Wrap in expected structure for parsing
                        wrapped_data = {"product": product_data}
                        product_info = self._parse_product_data(wrapped_data)
                        if product_info:
                            results.append(product_info)

                        if len(results) >= limit:
                            break

                    return results

        except Exception:
            # Graceful error handling
            pass

        return []

    async def __aenter__(self) -> "OpenFoodFactsAdapter":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit - cleanup session."""
        if self._session:
            await self._session.close()
            self._session = None
