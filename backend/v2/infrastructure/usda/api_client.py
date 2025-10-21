"""
USDA FoodData Central API client.

Handles HTTP requests with rate limiting and retries.
"""

import asyncio
import time
from typing import Optional

import aiohttp
import structlog

from backend.v2.domain.shared.errors import (
    ExternalServiceError,
    RateLimitError,
    TimeoutError,
)
from backend.v2.domain.meal.nutrition.usda_models import USDASearchResult
from backend.v2.domain.meal.nutrition.usda_mapper import USDAMapper
from backend.v2.domain.shared.value_objects import Barcode

logger = structlog.get_logger(__name__)


class RateLimiter:
    """Token bucket rate limiter.

    Ensures we don't exceed USDA API rate limits.
    """

    def __init__(self, requests_per_hour: int = 1000, burst_size: int = 10) -> None:
        """Initialize rate limiter.

        Args:
            requests_per_hour: Max requests per hour
            burst_size: Max burst requests
        """
        self.requests_per_hour = requests_per_hour
        self.burst_size = burst_size
        self.tokens = float(burst_size)
        self.last_update = time.time()
        self.lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Acquire token or wait.

        Raises:
            RateLimitError: If rate limit exceeded
        """
        async with self.lock:
            now = time.time()
            elapsed = now - self.last_update

            # Refill tokens based on time elapsed
            refill_rate = self.requests_per_hour / 3600.0
            self.tokens = min(self.burst_size, self.tokens + elapsed * refill_rate)
            self.last_update = now

            if self.tokens >= 1.0:
                self.tokens -= 1.0
            else:
                # Wait time for next token
                wait_time = (1.0 - self.tokens) / refill_rate
                if wait_time > 60:
                    msg = "Rate limit exceeded, wait time > 1 minute"
                    raise RateLimitError(msg)

                await asyncio.sleep(wait_time)
                self.tokens = 0.0


class USDAApiClient:
    """USDA FoodData Central API client."""

    BASE_URL = "https://api.nal.usda.gov/fdc/v1"

    def __init__(
        self,
        api_key: str,
        timeout_seconds: int = 10,
        max_retries: int = 3,
    ) -> None:
        """Initialize API client.

        Args:
            api_key: USDA API key
            timeout_seconds: Request timeout
            max_retries: Max retry attempts
        """
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.rate_limiter = RateLimiter()
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self) -> "USDAApiClient":
        """Async context manager entry."""
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, *args: object) -> None:
        """Async context manager exit."""
        if self._session:
            await self._session.close()

    async def search_by_barcode(self, barcode: Barcode) -> Optional[USDASearchResult]:
        """Search USDA database by barcode.

        Args:
            barcode: Product barcode

        Returns:
            Search result or None if not found

        Raises:
            RateLimitError: If rate limit exceeded
            TimeoutError: If request times out
            ExternalServiceError: If API error

        Example:
            >>> async def test():
            ...     async with USDAApiClient(api_key="test") as client:
            ...         barcode = Barcode(value="3017620422003")
            ...         result = await client.search_by_barcode(barcode)
            ...         return result
        """
        await self.rate_limiter.acquire()

        params = {
            "query": barcode.value,
            "dataType": ["Branded"],
            "pageSize": 1,
            "api_key": self.api_key,
        }

        url = f"{self.BASE_URL}/foods/search"

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
                    if response.status == 429:
                        msg = f"USDA API rate limit (attempt {attempt + 1})"
                        logger.warning(msg)
                        raise RateLimitError(msg)

                    if response.status == 404:
                        logger.info(
                            "Barcode not found in USDA",
                            barcode=barcode.value,
                        )
                        return None

                    if response.status >= 400:
                        msg = f"USDA API error: {response.status}"
                        raise ExternalServiceError(msg)

                    data = await response.json()
                    result = USDAMapper.parse_search_response(data)

                    if result.total_hits == 0:
                        return None

                    return result

            except asyncio.TimeoutError as e:
                if attempt == self.max_retries - 1:
                    msg = "USDA API timeout"
                    raise TimeoutError(msg) from e

                wait = 2**attempt
                logger.warning(
                    f"Timeout, retrying in {wait}s",
                    attempt=attempt + 1,
                )
                await asyncio.sleep(wait)

            except aiohttp.ClientError as e:
                if attempt == self.max_retries - 1:
                    msg = f"USDA API client error: {e}"
                    raise ExternalServiceError(msg) from e

                wait = 2**attempt
                await asyncio.sleep(wait)

        return None

    async def search_by_description(
        self, description: str, max_results: int = 5
    ) -> USDASearchResult:
        """Search USDA database by food description.

        Args:
            description: Food description
            max_results: Max results to return

        Returns:
            Search results

        Raises:
            RateLimitError: If rate limit exceeded
            TimeoutError: If request times out
            ExternalServiceError: If API error
        """
        await self.rate_limiter.acquire()

        params: dict[str, str | int] = {
            "query": description,
            "pageSize": max_results,
            "api_key": self.api_key,
        }

        url = f"{self.BASE_URL}/foods/search"

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
                    if response.status == 429:
                        msg = f"USDA rate limit (attempt {attempt + 1})"
                        raise RateLimitError(msg)

                    if response.status >= 400:
                        msg = f"USDA API error: {response.status}"
                        raise ExternalServiceError(msg)

                    data = await response.json()
                    return USDAMapper.parse_search_response(data)

            except asyncio.TimeoutError as e:
                if attempt == self.max_retries - 1:
                    msg = "USDA API timeout"
                    raise TimeoutError(msg) from e

                wait = 2**attempt
                await asyncio.sleep(wait)

            except aiohttp.ClientError as e:
                if attempt == self.max_retries - 1:
                    msg = f"USDA API client error: {e}"
                    raise ExternalServiceError(msg) from e

                wait = 2**attempt
                await asyncio.sleep(wait)

        # Should not reach here
        msg = "Max retries exceeded"
        raise ExternalServiceError(msg)
