"""Barcode provider port (interface).

Defines contract for barcode lookup services (e.g., OpenFoodFacts).
Follows the Dependency Inversion Principle: domain defines the port,
infrastructure provides the implementation.
"""

from typing import Optional, Protocol

from domain.meal.barcode.entities.barcode_product import BarcodeProduct


class IBarcodeProvider(Protocol):
    """
    Interface for barcode lookup services.

    This port defines the contract that infrastructure adapters must implement
    to provide barcode lookup functionality. Examples of implementations:
    - OpenFoodFacts client
    - UPC database client
    - Custom product database

    Example implementation (infrastructure layer):
        >>> class OpenFoodFactsClient:
        ...     async def lookup_barcode(self, barcode: str) -> Optional[BarcodeProduct]:
        ...         url = f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
        ...         response = await self._http_client.get(url)
        ...         if response["status"] == 1:
        ...             return self._map_to_barcode_product(response["product"])
        ...         return None

    Example usage (domain layer):
        >>> class BarcodeService:
        ...     def __init__(self, barcode_provider: IBarcodeProvider):
        ...         self._provider = barcode_provider
        ...
        ...     async def lookup(self, barcode: str) -> Optional[BarcodeProduct]:
        ...         return await self._provider.lookup_barcode(barcode)
    """

    async def lookup_barcode(self, barcode: str) -> Optional[BarcodeProduct]:
        """
        Look up product by barcode.

        Args:
            barcode: EAN/UPC code (e.g., "8001505005707")

        Returns:
            BarcodeProduct if found, None otherwise

        Raises:
            Exception: If network error, API error, or other infrastructure failure

        Example:
            >>> provider = OpenFoodFactsClient()
            >>> product = await provider.lookup_barcode("8001505005707")
            >>> if product:
            ...     print(f"Found: {product.display_name()}")
            ... else:
            ...     print("Product not found")
        """
        ...
