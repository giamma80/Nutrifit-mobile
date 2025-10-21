"""
OpenFoodFacts API client.

Handles HTTP requests to OpenFoodFacts database.
"""

import asyncio
from typing import Optional

import aiohttp
import structlog

from backend.v2.domain.shared.errors import (
    BarcodeNotFoundError,
    ExternalServiceError,
    TimeoutError,
)
from backend.v2.domain.meal.barcode.openfoodfacts_models import (
    OFFSearchResult,
)
from backend.v2.domain.meal.barcode.openfoodfacts_mapper import (
    OpenFoodFactsMapper,
)
from backend.v2.domain.shared.value_objects import Barcode

logger = structlog.get_logger(__name__)


class OpenFoodFactsClient:
    """OpenFoodFacts API client."""

    BASE_URL = "https://world.openfoodfacts.org/api/v2"
    USER_AGENT = "Nutrifit-Mobile/2.0"

    def __init__(
        self,
        timeout_seconds: int = 10,
        max_retries: int = 3,
    ) -> None:
        """Initialize API client.

        Args:
            timeout_seconds: Request timeout
            max_retries: Max retry attempts
        """
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self) -> "OpenFoodFactsClient":
        """Async context manager entry."""
        self._session = aiohttp.ClientSession(headers={"User-Agent": self.USER_AGENT})
        return self

    async def __aexit__(self, *args: object) -> None:
        """Async context manager exit."""
        if self._session:
            await self._session.close()

    async def get_product(self, barcode: Barcode) -> Optional[OFFSearchResult]:
        """Get product by barcode.

        Args:
            barcode: Product barcode

        Returns:
            Search result or None if not found

        Raises:
            BarcodeNotFoundError: If barcode not in database
            TimeoutError: If request times out
            ExternalServiceError: If API error

        Example:
            >>> async def test():
            ...     async with OpenFoodFactsClient() as client:
            ...         barcode = Barcode(value="3017620422003")
            ...         result = await client.get_product(barcode)
            ...         return result
        """
        url = f"{self.BASE_URL}/product/{barcode.value}"

        for attempt in range(self.max_retries):
            try:
                if not self._session:
                    msg = "Client not initialized, use async with"
                    raise ExternalServiceError(msg)

                async with self._session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=self.timeout_seconds),
                ) as response:
                    if response.status == 404:
                        logger.info(
                            "Barcode not found in OFF",
                            barcode=barcode.value,
                        )
                        raise BarcodeNotFoundError(f"Barcode {barcode.value} not found")

                    if response.status >= 400:
                        msg = f"OpenFoodFacts API error: {response.status}"
                        raise ExternalServiceError(msg)

                    data = await response.json()
                    result = OpenFoodFactsMapper.parse_product_response(data)

                    if not result.is_found():
                        logger.info(
                            "Product not found in OFF",
                            barcode=barcode.value,
                        )
                        raise BarcodeNotFoundError(f"Barcode {barcode.value} not found")

                    logger.info(
                        "Product found in OFF",
                        barcode=barcode.value,
                        name=result.product.product_name if result.product else None,
                    )

                    return result

            except BarcodeNotFoundError:
                # Don't retry on not found
                raise

            except asyncio.TimeoutError as e:
                if attempt == self.max_retries - 1:
                    msg = "OpenFoodFacts API timeout"
                    raise TimeoutError(msg) from e

                wait = 2**attempt
                logger.warning(
                    f"Timeout, retrying in {wait}s",
                    attempt=attempt + 1,
                )
                await asyncio.sleep(wait)

            except aiohttp.ClientError as e:
                if attempt == self.max_retries - 1:
                    msg = f"OpenFoodFacts API client error: {e}"
                    raise ExternalServiceError(msg) from e

                wait = 2**attempt
                await asyncio.sleep(wait)

        return None

    async def search_products(self, query: str, page_size: int = 5) -> list[OFFSearchResult]:
        """Search products by text query.

        Args:
            query: Search query
            page_size: Number of results

        Returns:
            List of search results

        Raises:
            TimeoutError: If request times out
            ExternalServiceError: If API error
        """
        url = f"{self.BASE_URL}/search"
        params: dict[str, str | int] = {
            "search_terms": query,
            "page_size": page_size,
            "json": "true",
        }

        for attempt in range(self.max_retries):
            try:
                if not self._session:
                    msg = "Client not initialized, use async with"
                    raise ExternalServiceError(msg)

                async with self._session.get(
                    url,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=self.timeout_seconds),
                ) as response:
                    if response.status >= 400:
                        msg = f"OpenFoodFacts API error: {response.status}"
                        raise ExternalServiceError(msg)

                    data = await response.json()

                    # Parse products from search results
                    results = []
                    for product_data in data.get("products", []):
                        wrapped = {"status": 1, "product": product_data}
                        result = OpenFoodFactsMapper.parse_product_response(wrapped)
                        if result.is_found():
                            results.append(result)

                    return results

            except asyncio.TimeoutError as e:
                if attempt == self.max_retries - 1:
                    msg = "OpenFoodFacts API timeout"
                    raise TimeoutError(msg) from e

                wait = 2**attempt
                await asyncio.sleep(wait)

            except aiohttp.ClientError as e:
                if attempt == self.max_retries - 1:
                    msg = f"OpenFoodFacts API client error: {e}"
                    raise ExternalServiceError(msg) from e

                wait = 2**attempt
                await asyncio.sleep(wait)

        return []
