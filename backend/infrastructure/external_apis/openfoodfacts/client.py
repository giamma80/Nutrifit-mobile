"""OpenFoodFacts API client - Implements IBarcodeProvider port.

Adapted from: openfoodfacts/adapter.py
Preserves all existing logic (nutrient extraction, fallbacks, retry) while implementing
the IBarcodeProvider port for dependency inversion.

Key Features:
- OpenFoodFacts API v2 product lookup
- Circuit breaker (5 failures → 60s timeout)
- Retry logic (exponential backoff)
- Nutrient extraction with fallbacks (energy kJ→kcal, salt→sodium)
- Metadata extraction (name, brand, category, image)
"""
# mypy: warn-unused-ignores=False

import asyncio
import logging
from typing import Optional, Dict, Any
from circuitbreaker import circuit
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

import httpx

from domain.meal.barcode.entities.barcode_product import BarcodeProduct
from domain.meal.nutrition.entities.nutrient_profile import NutrientProfile

logger = logging.getLogger(__name__)


class OpenFoodFactsClient:
    """
    OpenFoodFacts API client implementing IBarcodeProvider port.

    This adapter uses OpenFoodFacts API to implement the barcode provider port
    defined by the domain layer.

    Follows Dependency Inversion Principle:
    - Domain defines IBarcodeProvider interface (port)
    - Infrastructure provides OpenFoodFactsClient implementation (adapter)

    Example:
        >>> async with OpenFoodFactsClient() as client:
        ...     product = await client.lookup_barcode("8001505005707")
        ...     if product:
        ...         print(f"Found: {product.display_name()}")
    """

    BASE_URL = "https://world.openfoodfacts.org/api/v2/product"
    TIMEOUT_S = 8.0

    def __init__(self) -> None:
        """Initialize OpenFoodFacts client."""
        self._session: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "OpenFoodFactsClient":
        """Async context manager entry."""
        self._session = httpx.AsyncClient(
            timeout=httpx.Timeout(self.TIMEOUT_S)
        )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        if self._session:
            await self._session.aclose()

    @circuit(  # type: ignore[misc]
        failure_threshold=5, recovery_timeout=60, name="openfoodfacts_lookup"
    )
    @retry(  # type: ignore[misc]
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(
            (asyncio.TimeoutError, ConnectionError, httpx.HTTPError)
        ),
    )
    async def lookup_barcode(self, barcode: str) -> Optional[BarcodeProduct]:
        """
        Look up product by barcode.

        Implements IBarcodeProvider.lookup_barcode() port.

        Args:
            barcode: EAN/UPC code (e.g., "8001505005707")

        Returns:
            BarcodeProduct if found, None if not found

        Raises:
            Exception: On network or API errors (after retries)

        Example:
            >>> product = await client.lookup_barcode("8001505005707")
            >>> if product:
            ...     print(f"Calories: {product.nutrients.calories}")
        """
        if not self._session:
            raise RuntimeError(
                "Client not initialized. Use async context manager."
            )

        url = f"{self.BASE_URL}/{barcode}.json"

        logger.debug(
            "Looking up barcode",
            extra={"barcode": barcode},
        )

        try:
            response = await self._session.get(url)

            # Product not found - return None as per port contract
            if response.status_code == 404:
                logger.info(
                    "Barcode not found",
                    extra={"barcode": barcode},
                )
                return None

            # Server errors - let retry/circuit breaker handle
            if response.status_code >= 500:
                logger.warning(
                    "OpenFoodFacts server error",
                    extra={"barcode": barcode, "status": response.status_code},
                )
                raise httpx.HTTPError(f"Server error {response.status_code}")

            # Successful response
            if response.status_code == 200:
                data = response.json()
                status = data.get("status")

                # API returns status=0 for not found
                if status != 1:
                    logger.info(
                        "Product not found (status=0)",
                        extra={"barcode": barcode},
                    )
                    return None

                # Extract product data
                product_data = data.get("product", {})
                if not product_data:
                    logger.warning(
                        "Empty product data",
                        extra={"barcode": barcode},
                    )
                    return None

                # Map to domain entity
                barcode_product = self._map_to_barcode_product(
                    barcode, product_data
                )

                logger.info(
                    "Barcode lookup successful",
                    extra={
                        "barcode": barcode,
                        "product_name": barcode_product.name,
                    },
                )

                return barcode_product

            # Unexpected status code
            logger.warning(
                "Unexpected status code",
                extra={"barcode": barcode, "status": response.status_code},
            )
            return None

        except httpx.TimeoutException:
            logger.error(
                "OpenFoodFacts API timeout",
                extra={"barcode": barcode},
            )
            raise
        except Exception as e:
            logger.error(
                "OpenFoodFacts API error",
                extra={"barcode": barcode, "error": str(e)},
            )
            raise

    def _map_to_barcode_product(
        self, barcode: str, product_data: Dict[str, Any]
    ) -> BarcodeProduct:
        """
        Map OpenFoodFacts product data to BarcodeProduct domain entity.

        Preserves all existing nutrient extraction logic with fallbacks.

        Args:
            barcode: Product barcode
            product_data: OpenFoodFacts product JSON

        Returns:
            BarcodeProduct domain entity

        Raises:
            ValueError: If required data is missing
        """
        # Extract name (product_name or generic_name)
        name = (
            product_data.get("product_name")
            or product_data.get("generic_name")
            or "Unknown"
        )

        # Extract brand (first brand if multiple)
        brands = product_data.get("brands") or ""
        brand = brands.split(",")[0].strip() if brands else None

        # Extract image URL (prefer front image)
        image_url = product_data.get("image_front_url")

        # Extract nutrients
        nutrient_profile = self._extract_nutrients(product_data)

        return BarcodeProduct(
            barcode=barcode,
            name=name,
            brand=brand,
            nutrients=nutrient_profile,
            image_url=image_url,
            serving_size_g=100.0,  # OpenFoodFacts nutrients are per 100g
        )

    def _extract_nutrients(
        self, product_data: Dict[str, Any]
    ) -> NutrientProfile:
        """
        Extract nutrients from OpenFoodFacts product data.

        Preserves all existing logic:
        - Calories: prefer energy-kcal_100g, fallback to energy_100g / 4.184
        - Sodium: prefer sodium_100g, fallback to salt_100g * 400
        - Other nutrients: direct extraction with rounding

        Args:
            product_data: OpenFoodFacts product JSON

        Returns:
            NutrientProfile domain entity
        """
        nutriments = product_data.get("nutriments", {})

        def get_float(key: str) -> Optional[float]:
            """Extract float value from nutriments."""
            value = nutriments.get(key)
            try:
                return float(value) if value is not None else None
            except (TypeError, ValueError):
                return None

        # Calories: prefer energy-kcal_100g, fallback to kJ conversion
        calories = get_float("energy-kcal_100g")
        if calories is None:
            energy_kj = get_float("energy_100g")
            if energy_kj is not None:
                calories = energy_kj / 4.184

        # Macronutrients
        protein = get_float("proteins_100g")
        carbs = get_float("carbohydrates_100g")
        fat = get_float("fat_100g")
        fiber = get_float("fiber_100g")
        sugar = get_float("sugars_100g")

        # Sodium: prefer sodium_100g, fallback to salt conversion
        sodium = get_float("sodium_100g")
        if sodium is None:
            salt_g = get_float("salt_100g")
            if salt_g is not None:
                sodium = salt_g * 400  # approximate conversion

        # Create NutrientProfile with defaults for missing values
        return NutrientProfile(
            calories=int(round(calories)) if calories is not None else 0,
            protein=round(protein, 2) if protein is not None else 0.0,
            carbs=round(carbs, 2) if carbs is not None else 0.0,
            fat=round(fat, 2) if fat is not None else 0.0,
            fiber=round(fiber, 2) if fiber is not None else 0.0,
            sugar=round(sugar, 2) if sugar is not None else 0.0,
            sodium=round(sodium, 0) if sodium is not None else 0.0,
            quantity_g=100.0,  # OpenFoodFacts nutrients are per 100g
            source="BARCODE_DB",  # OpenFoodFacts is a barcode database
            confidence=0.90,  # OpenFoodFacts is high confidence source
        )
