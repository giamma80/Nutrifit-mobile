"""Domain service for barcode product lookup.

This service orchestrates barcode lookups using barcode providers
through the ports pattern.
"""

import logging
from typing import Optional

from domain.meal.barcode.entities.barcode_product import BarcodeProduct
from domain.meal.barcode.ports.barcode_provider import IBarcodeProvider

logger = logging.getLogger(__name__)


class BarcodeService:
    """
    Domain service for barcode product lookup.

    Delegates actual barcode lookups to barcode providers (e.g., OpenFoodFacts)
    while providing domain-level orchestration, validation, and logging.

    This service follows the ports pattern:
    - Service defines business logic
    - Port (IBarcodeProvider) defines contract
    - Infrastructure provides implementation

    Example:
        >>> from infrastructure.external_apis.openfoodfacts import OpenFoodFactsClient
        >>> provider = OpenFoodFactsClient()
        >>> service = BarcodeService(provider)
        >>> product = await service.lookup("8001505005707")
        >>> if product:
        ...     print(f"Found: {product.display_name()}")
        ...     print(f"Calories: {product.nutrients.calories} kcal")
    """

    def __init__(self, barcode_provider: IBarcodeProvider):
        """
        Initialize barcode service with provider.

        Args:
            barcode_provider: Implementation of IBarcodeProvider (e.g., OpenFoodFacts client)
        """
        self._provider = barcode_provider

    async def lookup(self, barcode: str) -> Optional[BarcodeProduct]:
        """
        Look up product by barcode.

        Args:
            barcode: EAN/UPC code (e.g., "8001505005707")

        Returns:
            BarcodeProduct if found, None if not found

        Raises:
            ValueError: If barcode is empty or invalid format
            Exception: If provider fails (network, API, etc.)

        Example:
            >>> service = BarcodeService(openfoodfacts_provider)
            >>> product = await service.lookup("8001505005707")
            >>> if product:
            ...     print(f"Found: {product.name}")
            ... else:
            ...     print("Product not found in database")
        """
        # Validate barcode
        if not barcode or not barcode.strip():
            raise ValueError("Barcode cannot be empty")

        # Clean barcode (remove spaces/dashes)
        clean_barcode = barcode.replace(" ", "").replace("-", "")

        if not clean_barcode.isalnum():
            raise ValueError("Barcode must be alphanumeric")

        logger.info(
            "Looking up barcode",
            extra={"barcode": clean_barcode},
        )

        try:
            product = await self._provider.lookup_barcode(clean_barcode)

            if product:
                logger.info(
                    "Barcode lookup successful",
                    extra={
                        "barcode": clean_barcode,
                        "product_name": product.name,
                        "has_brand": product.has_brand(),
                        "has_image": product.has_image(),
                        "high_quality": product.is_high_quality(),
                    },
                )
            else:
                logger.info(
                    "Barcode not found",
                    extra={"barcode": clean_barcode},
                )

            return product

        except Exception as e:
            logger.error(
                "Barcode lookup failed",
                extra={"barcode": clean_barcode, "error": str(e)},
                exc_info=True,
            )
            raise

    async def validate_product(self, product: BarcodeProduct, min_confidence: float = 0.7) -> bool:
        """
        Validate if barcode product data meets quality threshold.

        Args:
            product: Barcode product to validate
            min_confidence: Minimum nutrient data confidence (default: 0.7)

        Returns:
            True if product has reliable data (confidence >= threshold)

        Example:
            >>> product = await service.lookup("8001505005707")
            >>> if product and service.validate_product(product, min_confidence=0.8):
            ...     print("High quality product data!")
            ... else:
            ...     print("Low confidence data, manual review recommended")
        """
        is_valid = product.nutrients.confidence >= min_confidence

        logger.info(
            "Product validation",
            extra={
                "barcode": product.barcode,
                "confidence": product.nutrients.confidence,
                "min_confidence": min_confidence,
                "is_valid": is_valid,
                "source": product.nutrients.source,
            },
        )

        return is_valid
