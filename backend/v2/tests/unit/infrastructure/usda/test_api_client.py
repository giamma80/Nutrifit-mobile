"""
Unit tests for USDA API client.

Tests based on actual implementation with real-world test case:
Product: Barilla Pasta
Barcode: 8076804215898
Ingredients: Semola di grano duro, acqua
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import aiohttp

from v2.infrastructure.usda.api_client import RateLimiter, USDAApiClient


class TestRateLimiter:
    """Tests for token bucket rate limiter."""

    @pytest.mark.asyncio
    async def test_acquire_with_available_tokens(self) -> None:
        """Test token acquisition when tokens available."""
        limiter = RateLimiter(requests_per_hour=3600, burst_size=10)

        # Should acquire immediately
        await limiter.acquire()

        # Tokens should be reduced
        assert limiter.tokens < 10

    @pytest.mark.asyncio
    async def test_acquire_multiple_rapid_requests(self) -> None:
        """Test rapid successive requests within burst limit."""
        limiter = RateLimiter(requests_per_hour=3600, burst_size=5)

        # Should be able to make burst_size requests
        for _ in range(5):
            await limiter.acquire()

        # All tokens consumed
        assert limiter.tokens < 1.0

    @pytest.mark.asyncio
    async def test_acquire_waits_when_tokens_depleted(self) -> None:
        """Test that acquire waits when tokens are depleted."""
        # Higher rate to avoid 60s timeout
        limiter = RateLimiter(requests_per_hour=3600, burst_size=1)

        # First request OK
        await limiter.acquire()

        # Mock sleep to avoid actual waiting
        with patch("asyncio.sleep") as mock_sleep:
            await limiter.acquire()
            # Should have waited
            assert mock_sleep.called

    @pytest.mark.asyncio
    async def test_token_refill_over_time(self) -> None:
        """Test tokens refill based on elapsed time."""
        limiter = RateLimiter(requests_per_hour=36000, burst_size=10)

        # Deplete some tokens
        for _ in range(5):
            await limiter.acquire()

        # Wait for refill (36000/hr = 10/sec)
        await asyncio.sleep(0.1)

        # Should have refilled ~1 token, can acquire
        await limiter.acquire()

    @pytest.mark.asyncio
    async def test_acquire_actually_waits_when_depleted(self) -> None:
        """Test that acquire actually sleeps when tokens depleted."""
        # Fast refill to keep test quick (7200/hr = 2/sec)
        limiter = RateLimiter(requests_per_hour=7200, burst_size=1)

        # Deplete token
        await limiter.acquire()

        # This should actually wait and reset tokens to 0
        import time

        start = time.time()
        await limiter.acquire()
        elapsed = time.time() - start

        # Should have waited ~0.5s (half second for next token)
        assert elapsed > 0.4
        assert limiter.tokens < 0.1  # Should be near 0 after wait


class TestUSDAApiClient:
    """Tests for USDA FoodData Central API client."""

    @pytest.fixture
    def mock_search_response(self) -> MagicMock:
        """Create mock search response with Barilla pasta."""
        response = MagicMock()
        response.status = 200
        response.json = AsyncMock(
            return_value={
                "foods": [
                    {
                        "fdcId": 123456,
                        "description": "Barilla Pasta, Penne Rigate",
                        "dataType": "Branded",
                        "gtinUpc": "8076804215898",
                        "brandOwner": "Barilla",
                        "ingredients": "Semola di grano duro, acqua",
                        "foodNutrients": [
                            {"nutrientId": 1008, "value": 356},  # Energy
                            {"nutrientId": 1003, "value": 12},  # Protein
                            {"nutrientId": 1005, "value": 72.2},  # Carbs
                        ],
                    }
                ],
                "totalHits": 1,
                "currentPage": 1,
                "totalPages": 1,
            }
        )
        return response

    @pytest.mark.asyncio
    async def test_search_by_description_success(self, mock_search_response: MagicMock) -> None:
        """Test successful search by description."""
        async with USDAApiClient(api_key="test-key") as client:
            with patch("aiohttp.ClientSession.get") as mock_get:
                mock_get.return_value.__aenter__.return_value = mock_search_response

                result = await client.search_by_description("apple", max_results=5)

                assert result is not None
                assert result.total_hits == 1
                mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_by_barcode_success(self, mock_search_response: MagicMock) -> None:
        """Test successful barcode search with Barilla product."""
        from v2.domain.shared.value_objects import Barcode

        async with USDAApiClient(api_key="test-key") as client:
            with patch("aiohttp.ClientSession.get") as mock_get:
                mock_get.return_value.__aenter__.return_value = mock_search_response

                # Real Barilla product barcode
                barcode = Barcode(value="8076804215898")
                result = await client.search_by_barcode(barcode)

                assert result is not None
                assert result.total_hits == 1
                mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_by_barcode_not_found(self) -> None:
        """Test barcode search returns None when not found."""
        from v2.domain.shared.value_objects import Barcode

        empty_response = MagicMock()
        empty_response.status = 200
        empty_response.json = AsyncMock(
            return_value={
                "foods": [],
                "totalHits": 0,
                "currentPage": 1,
                "totalPages": 0,
            }
        )

        async with USDAApiClient(api_key="test-key") as client:
            with patch("aiohttp.ClientSession.get") as mock_get:
                mock_get.return_value.__aenter__.return_value = empty_response

                barcode = Barcode(value="999999999999")
                result = await client.search_by_barcode(barcode)

                assert result is None

    @pytest.mark.asyncio
    async def test_barcode_404_returns_none(self) -> None:
        """Test 404 response for barcode returns None."""
        from v2.domain.shared.value_objects import Barcode

        not_found_response = MagicMock()
        not_found_response.status = 404

        async with USDAApiClient(api_key="test-key") as client:
            with patch("aiohttp.ClientSession.get") as mock_get:
                mock_get.return_value.__aenter__.return_value = not_found_response

                barcode = Barcode(value="000000000000")
                result = await client.search_by_barcode(barcode)

                assert result is None

    @pytest.mark.asyncio
    async def test_rate_limiter_integration(self) -> None:
        """Test that rate limiter is applied to requests."""
        async with USDAApiClient(api_key="test-key") as client:
            # Rate limiter should exist
            assert client.rate_limiter is not None
            assert isinstance(client.rate_limiter, RateLimiter)

    @pytest.mark.asyncio
    async def test_context_manager_session_lifecycle(self) -> None:
        """Test async context manager creates and closes session."""
        client = USDAApiClient(api_key="test-key")

        # Session not created yet
        assert client._session is None

        async with client:
            # Session created on enter
            assert client._session is not None

    @pytest.mark.asyncio
    async def test_retry_with_exponential_backoff(self) -> None:
        """Test retries use exponential backoff."""
        async with USDAApiClient(api_key="test-key", max_retries=3) as client:
            with patch("aiohttp.ClientSession.get") as mock_get:
                with patch("asyncio.sleep") as mock_sleep:
                    mock_get.side_effect = asyncio.TimeoutError()

                    try:
                        await client.search_by_description("test")
                    except Exception:
                        pass

                    # Should sleep with exponential backoff: 1s, 2s
                    assert mock_sleep.call_count == 2
                    mock_sleep.assert_any_call(1)  # 2^0
                    mock_sleep.assert_any_call(2)  # 2^1

    @pytest.mark.asyncio
    async def test_real_barilla_product_simulation(self) -> None:
        """Test with realistic Barilla product data."""
        from v2.domain.shared.value_objects import Barcode

        # Simulate real USDA response for Barilla product
        barilla_response = MagicMock()
        barilla_response.status = 200
        barilla_response.json = AsyncMock(
            return_value={
                "foods": [
                    {
                        "fdcId": 789123,
                        "description": "BARILLA, PENNE RIGATE",
                        "dataType": "Branded",
                        "gtinUpc": "8076804215898",
                        "brandOwner": "BARILLA AMERICA, INC.",
                        "ingredients": "SEMOLA DI GRANO DURO, ACQUA",
                        "foodNutrients": [
                            {
                                "nutrientId": 1008,
                                "nutrientName": "Energy",
                                "value": 356,
                                "unitName": "KCAL",
                            },
                            {
                                "nutrientId": 1003,
                                "nutrientName": "Protein",
                                "value": 12,
                                "unitName": "G",
                            },
                            {
                                "nutrientId": 1005,
                                "nutrientName": "Carbohydrate, by difference",
                                "value": 72.2,
                                "unitName": "G",
                            },
                            {
                                "nutrientId": 2000,
                                "nutrientName": "Sugars, total",
                                "value": 3.5,
                                "unitName": "G",
                            },
                            {
                                "nutrientId": 1004,
                                "nutrientName": "Total lipid (fat)",
                                "value": 1.5,
                                "unitName": "G",
                            },
                            {
                                "nutrientId": 1079,
                                "nutrientName": "Fiber, total dietary",
                                "value": 3,
                                "unitName": "G",
                            },
                            {
                                "nutrientId": 1093,
                                "nutrientName": "Sodium, Na",
                                "value": 0.002,
                                "unitName": "G",
                            },
                        ],
                    }
                ],
                "totalHits": 1,
                "currentPage": 1,
                "totalPages": 1,
            }
        )

        async with USDAApiClient(api_key="test-key") as client:
            with patch("aiohttp.ClientSession.get") as mock_get:
                mock_get.return_value.__aenter__.return_value = barilla_response

                barcode = Barcode(value="8076804215898")
                result = await client.search_by_barcode(barcode)

                assert result is not None
                assert result.total_hits == 1
                # Verify it found the Barilla product
                assert len(result.foods) > 0

    @pytest.mark.asyncio
    async def test_search_by_description_empty_results(self) -> None:
        """Test search returns empty result with no foods (200 OK)."""
        empty_response = MagicMock()
        empty_response.status = 200
        empty_response.json = AsyncMock(
            return_value={
                "foods": [],
                "totalHits": 0,
                "currentPage": 1,
                "totalPages": 0,
            }
        )

        async with USDAApiClient(api_key="test-key") as client:
            with patch("aiohttp.ClientSession.get") as mock_get:
                mock_get.return_value.__aenter__.return_value = empty_response

                result = await client.search_by_description("nonexistent food xyz")

                # Empty results return SearchResult with empty foods list
                assert result is not None
                assert result.total_hits == 0
                assert len(result.foods) == 0

    @pytest.mark.asyncio
    async def test_rate_limiter_normal_wait(self) -> None:
        """Test rate limiter waits normally when tokens depleted (< 60s)."""
        # Configure for fast refill (avoid 60s timeout)
        limiter = RateLimiter(requests_per_hour=7200, burst_size=1)

        # Deplete tokens
        await limiter.acquire()

        # This should wait briefly and succeed (not raise)
        start = asyncio.get_event_loop().time()
        await limiter.acquire()
        elapsed = asyncio.get_event_loop().time() - start

        # Should have waited some time (but < 1 second with this rate)
        assert elapsed < 1.0






