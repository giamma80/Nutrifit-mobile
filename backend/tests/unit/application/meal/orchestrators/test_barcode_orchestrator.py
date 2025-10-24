"""Unit tests for BarcodeOrchestrator.

Tests focus on:
- Barcode lookup coordination
- Nutrient scaling
- Meal creation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from application.meal.orchestrators.barcode_orchestrator import BarcodeOrchestrator
from domain.meal.core.entities.meal import Meal
from domain.meal.barcode.entities.barcode_product import BarcodeProduct
from domain.meal.nutrition.entities.nutrient_profile import NutrientProfile


@pytest.fixture
def mock_barcode_service():
    return AsyncMock()


@pytest.fixture
def mock_nutrition_service():
    return AsyncMock()


@pytest.fixture
def mock_meal_factory():
    return MagicMock()


@pytest.fixture
def orchestrator(mock_barcode_service, mock_nutrition_service, mock_meal_factory):
    return BarcodeOrchestrator(
        barcode_service=mock_barcode_service,
        nutrition_service=mock_nutrition_service,
        meal_factory=mock_meal_factory
    )


@pytest.fixture
def sample_barcode_product_with_nutrients():
    nutrients = NutrientProfile(
        calories=220,
        protein=3.0,
        carbs=22.0,
        fat=15.0,
        fiber=2.0,
        sugar=20.0,
        sodium=40.0
    )
    return BarcodeProduct(
        barcode="8001505005707",
        name="Nutella",
        brand="Ferrero",
        nutrients=nutrients,
        image_url="https://example.com/nutella.jpg",
        serving_size_g=100.0
    )


@pytest.fixture
def sample_barcode_product_without_nutrients():
    return BarcodeProduct(
        barcode="1234567890123",
        name="Generic Product",
        brand=None,
        nutrients=None,
        image_url=None,
        serving_size_g=None
    )


@pytest.fixture
def sample_nutrient_profile():
    return NutrientProfile(
        calories=100,
        protein=5.0,
        carbs=15.0,
        fat=2.0,
        fiber=1.0,
        sugar=5.0,
        sodium=50.0
    )


@pytest.fixture
def sample_meal():
    meal = MagicMock(spec=Meal)
    meal.id = MagicMock()
    meal.entries = [MagicMock()]
    meal.total_calories = 330
    return meal


class TestBarcodeOrchestrator:
    """Test BarcodeOrchestrator."""

    @pytest.mark.asyncio
    async def test_analyze_with_product_nutrients(
        self,
        orchestrator,
        mock_barcode_service,
        mock_nutrition_service,
        mock_meal_factory,
        sample_barcode_product_with_nutrients,
        sample_meal
    ):
        """Test analysis when product has nutrients."""
        # Setup
        mock_barcode_service.lookup.return_value = sample_barcode_product_with_nutrients
        mock_meal_factory.create_from_analysis.return_value = sample_meal

        # Execute
        result = await orchestrator.analyze(
            user_id="user123",
            barcode="8001505005707",
            quantity_g=150.0,
            meal_type="SNACK"
        )

        # Assert
        assert result == sample_meal

        # Verify barcode lookup
        mock_barcode_service.lookup.assert_called_once_with("8001505005707")

        # Verify nutrition service NOT called (product has nutrients)
        mock_nutrition_service.enrich.assert_not_called()

        # Verify factory called with scaled nutrients
        mock_meal_factory.create_from_analysis.assert_called_once()
        call_args = mock_meal_factory.create_from_analysis.call_args
        assert call_args.kwargs["user_id"] == "user123"
        assert call_args.kwargs["source"] == "BARCODE"
        assert len(call_args.kwargs["items"]) == 1

        # Verify nutrients scaled (150g / 100g = 1.5x)
        food_dict, nutrients_dict = call_args.kwargs["items"][0]
        assert nutrients_dict["calories"] == int(220 * 1.5)  # 330

    @pytest.mark.asyncio
    async def test_analyze_without_product_nutrients(
        self,
        orchestrator,
        mock_barcode_service,
        mock_nutrition_service,
        mock_meal_factory,
        sample_barcode_product_without_nutrients,
        sample_nutrient_profile,
        sample_meal
    ):
        """Test analysis when product lacks nutrients (USDA fallback)."""
        # Setup
        mock_barcode_service.lookup.return_value = sample_barcode_product_without_nutrients
        mock_nutrition_service.enrich.return_value = sample_nutrient_profile
        mock_meal_factory.create_from_analysis.return_value = sample_meal

        # Execute
        result = await orchestrator.analyze(
            user_id="user123",
            barcode="1234567890123",
            quantity_g=200.0,
            meal_type="SNACK"
        )

        # Assert
        assert result == sample_meal

        # Verify enrichment called (fallback to USDA)
        mock_nutrition_service.enrich.assert_called_once_with(
            label="Generic Product",
            quantity_g=100.0,
            category=None
        )

    @pytest.mark.asyncio
    async def test_analyze_product_not_found(
        self,
        orchestrator,
        mock_barcode_service
    ):
        """Test analysis fails when product not found."""
        mock_barcode_service.lookup.return_value = None

        with pytest.raises(ValueError, match="Product not found"):
            await orchestrator.analyze(
                user_id="user123",
                barcode="9999999999999",
                quantity_g=100.0
            )
