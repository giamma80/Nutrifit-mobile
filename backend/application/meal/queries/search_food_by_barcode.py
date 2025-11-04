"""Search food by barcode query - utility to test barcode lookup capability."""

from dataclasses import dataclass
import logging

from domain.meal.barcode.entities.barcode_product import BarcodeProduct
from domain.meal.barcode.services.barcode_service import BarcodeService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SearchFoodByBarcodeQuery:
    """
    Utility Query: Search food product by barcode.

    Atomic query to test barcode lookup without creating meals.
    Useful for:
    - Testing OpenFoodFacts API integration
    - Debug/troubleshooting
    - Preview product info before meal creation

    Attributes:
        barcode: Product barcode (EAN/UPC)
    """

    barcode: str


class SearchFoodByBarcodeQueryHandler:
    """Handler for SearchFoodByBarcodeQuery."""

    def __init__(self, barcode_service: BarcodeService):
        """
        Initialize handler.

        Args:
            barcode_service: Barcode lookup service
        """
        self._barcode = barcode_service

    async def handle(self, query: SearchFoodByBarcodeQuery) -> BarcodeProduct:
        """
        Execute barcode lookup query.

        Args:
            query: SearchFoodByBarcodeQuery

        Returns:
            BarcodeProduct with product information

        Raises:
            ValueError: If barcode not found or invalid

        Example:
            >>> handler = SearchFoodByBarcodeQueryHandler(barcode_service)
            >>> query = SearchFoodByBarcodeQuery(barcode="8001505005707")
            >>> product = await handler.handle(query)
            >>> product.name is not None
            True
        """
        logger.info(
            "Looking up product by barcode",
            extra={"barcode": query.barcode},
        )

        # Lookup product via barcode service
        product = await self._barcode.lookup(query.barcode)

        if not product:
            logger.warning(
                "Barcode not found",
                extra={"barcode": query.barcode},
            )
            raise ValueError(f"Product not found for barcode: {query.barcode}")

        logger.info(
            "Barcode lookup completed",
            extra={
                "barcode": query.barcode,
                "product_name": product.name,
                "brand": product.brand,
                "has_nutrients": product.nutrients is not None,
                "has_image": product.has_image(),
                "is_high_quality": product.is_high_quality() if product.nutrients else False,
            },
        )

        return product
