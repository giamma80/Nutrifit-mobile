"""Unit tests for SearchFoodByBarcodeQuery and handler."""

import pytest
from unittest.mock import AsyncMock

from application.meal.queries.search_food_by_barcode import (
    SearchFoodByBarcodeQuery,
    SearchFoodByBarcodeQueryHandler,
)
from domain.meal.barcode.entities.barcode_product import BarcodeProduct
from domain.meal.nutrition.entities.nutrient_profile import NutrientProfile


@pytest.fixture
def mock_barcode_service():
    return AsyncMock()


@pytest.fixture
def handler(mock_barcode_service):
    return SearchFoodByBarcodeQueryHandler(barcode_service=mock_barcode_service)


@pytest.fixture
def sample_barcode_product():
    nutrients = NutrientProfile(
        calories=220.0, protein=3.5, carbs=30.0, fat=10.0, fiber=2.0, sugar=25.0, sodium=100.0
    )

    return BarcodeProduct(
        barcode="8001505005707",
        name="Nutella",
        brand="Ferrero",
        nutrients=nutrients,
        serving_size_g=100.0,
        image_url="https://example.com/nutella.jpg",
    )


class TestSearchFoodByBarcodeQueryHandler:
    """Test SearchFoodByBarcodeQueryHandler."""

    @pytest.mark.asyncio
    async def test_search_barcode_success(
        self, handler, mock_barcode_service, sample_barcode_product
    ):
        """Test successful barcode lookup."""
        query = SearchFoodByBarcodeQuery(barcode="8001505005707")

        mock_barcode_service.lookup.return_value = sample_barcode_product

        result = await handler.handle(query)

        assert result == sample_barcode_product
        mock_barcode_service.lookup.assert_called_once_with("8001505005707")

    @pytest.mark.asyncio
    async def test_search_barcode_not_found(self, handler, mock_barcode_service):
        """Test barcode not found."""
        query = SearchFoodByBarcodeQuery(barcode="9999999999999")

        # Service returns None for not found
        mock_barcode_service.lookup.return_value = None

        # Handler should raise ValueError
        with pytest.raises(ValueError, match="Product not found"):
            await handler.handle(query)

    @pytest.mark.asyncio
    async def test_search_barcode_product_with_nutrients(
        self, handler, mock_barcode_service, sample_barcode_product
    ):
        """Test product with full nutrient information."""
        query = SearchFoodByBarcodeQuery(barcode="8001505005707")

        mock_barcode_service.lookup.return_value = sample_barcode_product

        result = await handler.handle(query)

        assert result.nutrients is not None
        assert result.nutrients.calories == 220.0

    @pytest.mark.asyncio
    async def test_search_barcode_product_without_nutrients(self, handler, mock_barcode_service):
        """Test product without nutrient information."""
        product = BarcodeProduct(
            barcode="1234567890123",
            name="Generic Product",
            brand="Unknown",
            nutrients=None,  # No nutrients
            serving_size_g=100.0,
            image_url=None,
        )

        query = SearchFoodByBarcodeQuery(barcode="1234567890123")

        mock_barcode_service.lookup.return_value = product

        result = await handler.handle(query)

        assert result.nutrients is None
        assert result.name == "Generic Product"
