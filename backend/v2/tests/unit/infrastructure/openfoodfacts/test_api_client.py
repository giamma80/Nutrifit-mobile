"""
Unit tests for OpenFoodFacts API client.

Tests based on actual implementation with real-world test case:
Product: Nutella, Barcode: 3017620422003
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.v2.domain.meal.barcode.openfoodfacts_models import (
    NovaGroup,
    NutriscoreGrade,
)
from backend.v2.domain.shared.errors import BarcodeNotFoundError
from backend.v2.domain.shared.value_objects import Barcode
from backend.v2.infrastructure.openfoodfacts.api_client import (
    OpenFoodFactsClient,
)


class TestOpenFoodFactsClient:
    """Test OpenFoodFacts API client."""

    @pytest.fixture
    def mock_nutella_response(self) -> MagicMock:
        """Mock response with real Nutella product data.

        Real product: Nutella (Ferrero), Barcode: 3017620422003
        """
        response = MagicMock()
        response.status = 200
        response.json = AsyncMock(
            return_value={
                "status": 1,
                "product": {
                    "code": "3017620422003",
                    "product_name": "Nutella",
                    "brands": "Ferrero",
                    "categories": "Spreads, Sweet spreads, Chocolate spreads",
                    "quantity": "750g",
                    "serving_size": "15g",
                    "image_url": "https://images.openfoodfacts.org/images/products/301/762/042/2003/front_en.jpg",
                    "nutriscore_grade": "e",
                    "nova_group": 4,
                    "ingredients_text": "Sugar, palm oil, hazelnuts (13%), skimmed milk powder (8.7%), "
                    "fat-reduced cocoa (7.4%), emulsifier: lecithins (soya), vanillin.",
                    "allergens": "Milk, Nuts, Soybeans",
                    "nutriments": {
                        "energy-kcal_100g": 539.0,
                        "proteins_100g": 6.3,
                        "carbohydrates_100g": 57.5,
                        "fat_100g": 30.9,
                        "fiber_100g": 0.0,
                        "sugars_100g": 56.3,
                        "sodium_100g": 0.107,
                        "salt_100g": 0.27,
                    },
                },
            }
        )
        return response

    @pytest.fixture
    def mock_search_response(self) -> MagicMock:
        """Mock search response with multiple products."""
        response = MagicMock()
        response.status = 200
        response.json = AsyncMock(
            return_value={
                "products": [
                    {
                        "code": "3017620422003",
                        "product_name": "Nutella",
                        "brands": "Ferrero",
                        "nutriments": {
                            "energy-kcal_100g": 539.0,
                            "proteins_100g": 6.3,
                            "carbohydrates_100g": 57.5,
                            "fat_100g": 30.9,
                        },
                    },
                    {
                        "code": "8076809513838",
                        "product_name": "Kinder Bueno",
                        "brands": "Ferrero",
                        "nutriments": {
                            "energy-kcal_100g": 571.0,
                            "proteins_100g": 9.1,
                            "carbohydrates_100g": 49.5,
                            "fat_100g": 37.3,
                        },
                    },
                ]
            }
        )
        return response

    async def test_get_product_success(self, mock_nutella_response: MagicMock) -> None:
        """Test successful product retrieval by barcode."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_nutella_response

            async with OpenFoodFactsClient() as client:
                barcode = Barcode(value="3017620422003")
                result = await client.get_product(barcode)

                assert result is not None
                assert result.status == 1
                assert result.product is not None
                assert result.product.code == "3017620422003"
                assert result.product.product_name == "Nutella"
                assert result.product.brands == "Ferrero"
                assert result.product.nutriscore_grade == NutriscoreGrade.E
                assert result.product.nova_group == NovaGroup.GROUP_4

    async def test_get_product_not_found_404(self) -> None:
        """Test product not found with 404 status."""
        response = MagicMock()
        response.status = 404

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.return_value.__aenter__.return_value = response

            async with OpenFoodFactsClient() as client:
                barcode = Barcode(value="9999999999999")

                with pytest.raises(BarcodeNotFoundError) as exc_info:
                    await client.get_product(barcode)

                assert "9999999999999" in str(exc_info.value)

    async def test_get_product_not_found_status_zero(self) -> None:
        """Test product not found when API returns status=0."""
        response = MagicMock()
        response.status = 200
        response.json = AsyncMock(return_value={"status": 0})

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.return_value.__aenter__.return_value = response

            async with OpenFoodFactsClient() as client:
                barcode = Barcode(value="9999999999999")

                with pytest.raises(BarcodeNotFoundError):
                    await client.get_product(barcode)

    async def test_search_products_success(self, mock_search_response: MagicMock) -> None:
        """Test successful product search."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_search_response

            async with OpenFoodFactsClient() as client:
                results = await client.search_products("chocolate", page_size=5)

                assert len(results) == 2
                assert results[0].product is not None
                assert results[0].product.product_name == "Nutella"
                assert results[1].product is not None
                assert results[1].product.product_name == "Kinder Bueno"

    async def test_search_products_empty_results(self) -> None:
        """Test search with no results."""
        response = MagicMock()
        response.status = 200
        response.json = AsyncMock(return_value={"products": []})

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.return_value.__aenter__.return_value = response

            async with OpenFoodFactsClient() as client:
                results = await client.search_products("nonexistentproduct12345")

                assert results == []

    async def test_context_manager_session_lifecycle(self) -> None:
        """Test that async context manager creates and closes session."""
        client = OpenFoodFactsClient()
        assert client._session is None

        async with client:
            assert client._session is not None

        # Session should be closed after exit (we can't check directly, but no error)

    async def test_custom_timeout(self, mock_nutella_response: MagicMock) -> None:
        """Test custom timeout configuration."""
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_nutella_response

            async with OpenFoodFactsClient(timeout_seconds=5) as client:
                assert client.timeout_seconds == 5
                barcode = Barcode(value="3017620422003")
                await client.get_product(barcode)

                # Verify timeout was used
                mock_get.assert_called_once()

    async def test_user_agent_header(self) -> None:
        """Test that User-Agent header is set correctly."""
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            async with OpenFoodFactsClient():
                mock_session_class.assert_called_once_with(
                    headers={"User-Agent": "Nutrifit-Mobile/2.0"}
                )

    async def test_real_nutella_product_simulation(self, mock_nutella_response: MagicMock) -> None:
        """Test with comprehensive Nutella product data.

        Real product: Nutella (Ferrero), Barcode: 3017620422003
        Source: OpenFoodFacts database
        """
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.return_value.__aenter__.return_value = mock_nutella_response

            async with OpenFoodFactsClient() as client:
                barcode = Barcode(value="3017620422003")
                result = await client.get_product(barcode)

                # Verify product found
                assert result is not None
                assert result.is_found() is True

                # Verify product details
                product = result.product
                assert product is not None
                assert product.code == "3017620422003"
                assert product.product_name == "Nutella"
                assert product.brands == "Ferrero"

                # Verify nutritional data (per 100g)
                assert product.nutriments is not None
                n = product.nutriments
                assert n.energy_kcal == 539.0
                assert n.proteins == 6.3
                assert n.carbohydrates == 57.5
                assert n.fat == 30.9
                assert n.fiber == 0.0
                assert n.sugars == 56.3
                assert n.sodium == 0.107
                assert n.salt == 0.27

                # Verify quality indicators
                assert product.nutriscore_grade == NutriscoreGrade.E  # Worst grade
                assert product.nova_group == NovaGroup.GROUP_4  # Ultra-processed

                # Verify additional info
                assert product.quantity == "750g"
                assert product.serving_size == "15g"
                assert "hazelnuts" in product.ingredients_text.lower()
                assert "milk" in product.allergens.lower()
