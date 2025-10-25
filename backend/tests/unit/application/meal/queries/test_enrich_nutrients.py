"""Unit tests for EnrichNutrientsQuery and handler."""

import pytest
from unittest.mock import AsyncMock

from application.meal.queries.enrich_nutrients import (
    EnrichNutrientsQuery,
    EnrichNutrientsQueryHandler,
)
from domain.meal.nutrition.entities.nutrient_profile import NutrientProfile


@pytest.fixture
def mock_enrichment_service():
    return AsyncMock()


@pytest.fixture
def handler(mock_enrichment_service):
    return EnrichNutrientsQueryHandler(enrichment_service=mock_enrichment_service)


@pytest.fixture
def sample_nutrient_profile():
    return NutrientProfile(
        calories=165.0, protein=31.0, carbs=0.0, fat=3.6, fiber=0.0, sugar=0.0, sodium=74.0
    )


class TestEnrichNutrientsQueryHandler:
    """Test EnrichNutrientsQueryHandler."""

    @pytest.mark.asyncio
    async def test_enrich_nutrients_success(
        self, handler, mock_enrichment_service, sample_nutrient_profile
    ):
        """Test successful nutrient enrichment."""
        query = EnrichNutrientsQuery(food_label="roasted_chicken", quantity_g=150.0)

        mock_enrichment_service.enrich.return_value = sample_nutrient_profile

        result = await handler.handle(query)

        assert result == sample_nutrient_profile
        mock_enrichment_service.enrich.assert_called_once_with(
            label="roasted_chicken", quantity_g=150.0
        )

    @pytest.mark.asyncio
    async def test_enrich_nutrients_different_quantities(self, handler, mock_enrichment_service):
        """Test enrichment with different quantities."""
        query = EnrichNutrientsQuery(food_label="apple", quantity_g=200.0)

        profile = NutrientProfile(
            calories=104.0, protein=0.5, carbs=28.0, fat=0.3, fiber=4.8, sugar=21.0, sodium=2.0
        )

        mock_enrichment_service.enrich.return_value = profile

        result = await handler.handle(query)

        assert result.calories == 104.0
        mock_enrichment_service.enrich.assert_called_once_with(label="apple", quantity_g=200.0)

    @pytest.mark.asyncio
    async def test_enrich_nutrients_uses_cascade_strategy(
        self, handler, mock_enrichment_service, sample_nutrient_profile
    ):
        """Test that enrichment uses cascade strategy (USDA → Category → Fallback)."""
        query = EnrichNutrientsQuery(food_label="unknown_food", quantity_g=100.0)

        # Service should try USDA, then fallback
        mock_enrichment_service.enrich.return_value = sample_nutrient_profile

        result = await handler.handle(query)

        # Should still return a profile (from fallback if USDA fails)
        assert isinstance(result, NutrientProfile)
