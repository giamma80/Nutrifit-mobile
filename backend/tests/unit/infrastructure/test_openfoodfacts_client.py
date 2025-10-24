"""Unit tests for OpenFoodFacts Client.

Tests focus on:
- Client initialization
- Barcode lookup functionality
- Nutrient extraction and mapping with fallbacks
- IBarcodeProvider port implementation
- Error handling

Note: These are UNIT tests with mocked OpenFoodFacts API calls.
For integration tests with real API, see:
tests/integration/infrastructure/test_openfoodfacts_integration.py
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import Any

from infrastructure.external_apis.openfoodfacts.client import OpenFoodFactsClient
from domain.meal.barcode.entities.barcode_product import BarcodeProduct


@pytest.fixture
def off_client() -> OpenFoodFactsClient:
    """Fixture providing OpenFoodFactsClient with mocked HTTP session."""
    client = OpenFoodFactsClient()
    # Mock the session directly (don't use async context manager in tests)
    client._session = AsyncMock()
    return client


@pytest.fixture
def sample_off_response() -> dict[str, Any]:
    """Sample OpenFoodFacts API response."""
    return {
        "status": 1,
        "product": {
            "product_name": "Galletti Biscuits",
            "brands": "Mulino Bianco",
            "image_front_url": (
                "https://images.openfoodfacts.org/images/products/" "800/150/500/5707/front_it.jpg"
            ),
            "nutriments": {
                "energy-kcal_100g": 450,
                "proteins_100g": 7.5,
                "carbohydrates_100g": 70.0,
                "fat_100g": 15.0,
                "fiber_100g": 3.0,
                "sugars_100g": 22.0,
                "sodium_100g": 200,
            },
        },
    }


@pytest.fixture
def sample_off_response_with_fallbacks() -> dict[str, Any]:
    """Sample OpenFoodFacts response requiring fallback conversions."""
    return {
        "status": 1,
        "product": {
            "product_name": "Test Product",
            "generic_name": "Generic Food",
            "brands": "",
            "nutriments": {
                # Energy in kJ (requires conversion to kcal)
                "energy_100g": 1884,  # ~450 kcal
                "proteins_100g": 5.0,
                "carbohydrates_100g": 60.0,
                "fat_100g": 10.0,
                # Salt instead of sodium (requires conversion)
                "salt_100g": 0.5,  # ~200mg sodium
            },
        },
    }


class TestOpenFoodFactsClientInit:
    """Test client initialization."""

    def test_init(self) -> None:
        """Test initialization."""
        client = OpenFoodFactsClient()
        assert client._session is None


class TestLookupBarcode:
    """Test lookup_barcode method."""

    @pytest.mark.asyncio
    async def test_lookup_barcode_success(
        self, off_client: OpenFoodFactsClient, sample_off_response: dict[str, Any]
    ) -> None:
        """Test successful barcode lookup."""
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value=sample_off_response)

        off_client._session.get = AsyncMock(return_value=mock_response)

        # Execute
        product = await off_client.lookup_barcode("8001505005707")

        # Assert
        assert product is not None
        assert isinstance(product, BarcodeProduct)
        assert product.barcode == "8001505005707"
        assert product.name == "Galletti Biscuits"
        assert product.brand == "Mulino Bianco"
        assert product.nutrients.calories == 450
        assert product.nutrients.protein == 7.5
        assert product.nutrients.carbs == 70.0
        assert product.nutrients.fat == 15.0
        assert product.nutrients.fiber == 3.0
        assert product.nutrients.sugar == 22.0
        assert product.nutrients.sodium == 200
        assert product.nutrients.source == "BARCODE_DB"
        assert product.nutrients.confidence == 0.90
        assert product.image_url is not None
        assert product.serving_size_g == 100.0

    @pytest.mark.asyncio
    async def test_lookup_barcode_with_fallbacks(
        self,
        off_client: OpenFoodFactsClient,
        sample_off_response_with_fallbacks: dict[str, Any],
    ) -> None:
        """Test barcode lookup with fallback conversions."""
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value=sample_off_response_with_fallbacks)

        off_client._session.get = AsyncMock(return_value=mock_response)

        # Execute
        product = await off_client.lookup_barcode("1234567890123")

        # Assert
        assert product is not None
        # Energy kJ → kcal conversion: 1884 / 4.184 ≈ 450
        assert product.nutrients.calories == 450
        # Salt → sodium conversion: 0.5g * 400 = 200mg
        assert product.nutrients.sodium == 200
        # Uses generic_name as fallback
        assert product.name == "Test Product"
        # Empty brand becomes None
        assert product.brand is None

    @pytest.mark.asyncio
    async def test_lookup_barcode_not_found_404(self, off_client: OpenFoodFactsClient) -> None:
        """Test barcode lookup with 404 response."""
        # Mock HTTP 404 response
        mock_response = MagicMock()
        mock_response.status_code = 404

        off_client._session.get = AsyncMock(return_value=mock_response)

        # Execute
        product = await off_client.lookup_barcode("0000000000000")

        # Assert - should return None for not found
        assert product is None

    @pytest.mark.asyncio
    async def test_lookup_barcode_not_found_status_0(self, off_client: OpenFoodFactsClient) -> None:
        """Test barcode lookup with status=0 (not found)."""
        # Mock HTTP response with status=0
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={"status": 0})

        off_client._session.get = AsyncMock(return_value=mock_response)

        # Execute
        product = await off_client.lookup_barcode("0000000000000")

        # Assert - should return None for status=0
        assert product is None

    @pytest.mark.asyncio
    async def test_lookup_barcode_empty_product(self, off_client: OpenFoodFactsClient) -> None:
        """Test barcode lookup with empty product data."""
        # Mock HTTP response with empty product
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={"status": 1, "product": {}})

        off_client._session.get = AsyncMock(return_value=mock_response)

        # Execute
        product = await off_client.lookup_barcode("1234567890123")

        # Assert - should return None for empty product
        assert product is None

    @pytest.mark.asyncio
    async def test_lookup_barcode_server_error(self, off_client: OpenFoodFactsClient) -> None:
        """Test barcode lookup with server error."""
        # Mock HTTP 500 response
        mock_response = MagicMock()
        mock_response.status_code = 500

        off_client._session.get = AsyncMock(return_value=mock_response)

        # Execute - should raise exception (retry/circuit breaker will handle)
        with pytest.raises(Exception):
            await off_client.lookup_barcode("1234567890123")


class TestNutrientExtraction:
    """Test _extract_nutrients method."""

    def test_extract_nutrients_complete_data(self) -> None:
        """Test extraction with complete nutrient data."""
        client = OpenFoodFactsClient()

        product_data = {
            "nutriments": {
                "energy-kcal_100g": 500,
                "proteins_100g": 10.0,
                "carbohydrates_100g": 60.0,
                "fat_100g": 20.0,
                "fiber_100g": 5.0,
                "sugars_100g": 15.0,
                "sodium_100g": 300,
            }
        }

        nutrients = client._extract_nutrients(product_data)

        assert nutrients.calories == 500
        assert nutrients.protein == 10.0
        assert nutrients.carbs == 60.0
        assert nutrients.fat == 20.0
        assert nutrients.fiber == 5.0
        assert nutrients.sugar == 15.0
        assert nutrients.sodium == 300
        assert nutrients.quantity_g == 100.0
        assert nutrients.source == "BARCODE_DB"
        assert nutrients.confidence == 0.90

    def test_extract_nutrients_energy_kj_fallback(self) -> None:
        """Test energy conversion from kJ to kcal."""
        client = OpenFoodFactsClient()

        product_data = {
            "nutriments": {
                "energy_100g": 2092,  # 500 kcal
            }
        }

        nutrients = client._extract_nutrients(product_data)

        # 2092 / 4.184 ≈ 500
        assert nutrients.calories == 500

    def test_extract_nutrients_salt_to_sodium_fallback(self) -> None:
        """Test sodium conversion from salt."""
        client = OpenFoodFactsClient()

        product_data = {
            "nutriments": {
                "salt_100g": 0.75,  # 300mg sodium
            }
        }

        nutrients = client._extract_nutrients(product_data)

        # 0.75g * 400 = 300mg
        assert nutrients.sodium == 300

    def test_extract_nutrients_missing_values(self) -> None:
        """Test extraction with missing nutrient values."""
        client = OpenFoodFactsClient()

        product_data = {"nutriments": {}}

        nutrients = client._extract_nutrients(product_data)

        # All values should default to 0
        assert nutrients.calories == 0
        assert nutrients.protein == 0.0
        assert nutrients.carbs == 0.0
        assert nutrients.fat == 0.0
        assert nutrients.fiber == 0.0
        assert nutrients.sugar == 0.0
        assert nutrients.sodium == 0.0


class TestProductMapping:
    """Test _map_to_barcode_product method."""

    def test_map_to_barcode_product_complete(self, sample_off_response: dict[str, Any]) -> None:
        """Test mapping with complete product data."""
        client = OpenFoodFactsClient()

        product = client._map_to_barcode_product("8001505005707", sample_off_response["product"])

        assert product.barcode == "8001505005707"
        assert product.name == "Galletti Biscuits"
        assert product.brand == "Mulino Bianco"
        assert product.has_brand()
        assert product.has_image()
        assert product.serving_size_g == 100.0

    def test_map_to_barcode_product_no_brand(self) -> None:
        """Test mapping with missing brand."""
        client = OpenFoodFactsClient()

        product_data = {
            "product_name": "Generic Crackers",
            "brands": "",
            "nutriments": {},
        }

        product = client._map_to_barcode_product("1234567890123", product_data)

        assert product.name == "Generic Crackers"
        assert product.brand is None
        assert not product.has_brand()

    def test_map_to_barcode_product_generic_name_fallback(self) -> None:
        """Test name fallback to generic_name."""
        client = OpenFoodFactsClient()

        product_data = {
            "generic_name": "Generic Food Item",
            "nutriments": {},
        }

        product = client._map_to_barcode_product("1234567890123", product_data)

        assert product.name == "Generic Food Item"

    def test_map_to_barcode_product_unknown_name(self) -> None:
        """Test name fallback to 'Unknown'."""
        client = OpenFoodFactsClient()

        product_data = {"nutriments": {}}

        product = client._map_to_barcode_product("1234567890123", product_data)

        assert product.name == "Unknown"
