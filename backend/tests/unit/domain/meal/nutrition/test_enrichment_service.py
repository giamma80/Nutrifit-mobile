"""Unit tests for NutritionEnrichmentService.

Tests the cascade strategy with mocked providers.
"""

import pytest
from typing import Optional

from domain.meal.nutrition.entities import NutrientProfile
from domain.meal.nutrition.services import NutritionEnrichmentService


# Mock provider implementations for testing
class MockUSDAProvider:
    """Mock USDA provider."""

    def __init__(self, return_value: Optional[NutrientProfile] = None, should_raise: bool = False):
        self.return_value = return_value
        self.should_raise = should_raise
        self.called_with: list[tuple[str, float]] = []

    async def get_nutrients(self, identifier: str, quantity_g: float) -> Optional[NutrientProfile]:
        self.called_with.append((identifier, quantity_g))
        if self.should_raise:
            raise Exception("USDA API error")
        return self.return_value


class MockCategoryProvider:
    """Mock category provider."""

    def __init__(self, return_value: Optional[NutrientProfile] = None, should_raise: bool = False):
        self.return_value = return_value
        self.should_raise = should_raise
        self.called_with: list[tuple[str, float]] = []

    async def get_nutrients(self, identifier: str, quantity_g: float) -> Optional[NutrientProfile]:
        self.called_with.append((identifier, quantity_g))
        if self.should_raise:
            raise Exception("Category lookup error")
        return self.return_value


class MockFallbackProvider:
    """Mock fallback provider."""

    def __init__(self) -> None:
        self.called_with: list[tuple[str, float]] = []

    async def get_nutrients(self, identifier: str, quantity_g: float) -> Optional[NutrientProfile]:
        self.called_with.append((identifier, quantity_g))
        # Fallback always returns a generic profile
        return NutrientProfile(
            calories=100,
            protein=5.0,
            carbs=15.0,
            fat=3.0,
            source="AI_ESTIMATE",
            confidence=0.3,
            quantity_g=100.0,
        )


class TestEnrichmentServiceCascade:
    """Test suite for enrichment cascade strategy."""

    @pytest.mark.asyncio
    async def test_uses_usda_if_available(self) -> None:
        """Test that USDA provider is used first if it returns data."""
        usda_profile = NutrientProfile(
            calories=165,
            protein=31.0,
            carbs=0.0,
            fat=3.6,
            source="USDA",
            confidence=0.95,
            quantity_g=100.0,
        )

        usda = MockUSDAProvider(return_value=usda_profile)
        category = MockCategoryProvider()
        fallback = MockFallbackProvider()

        service = NutritionEnrichmentService(usda, category, fallback)

        result = await service.enrich("chicken breast", 150.0, "meat")

        # Should use USDA and scale to 150g
        assert result.calories == 247  # 165 * 1.5
        assert result.protein == 46.5  # 31 * 1.5
        assert result.source == "USDA"
        assert result.quantity_g == 150.0

        # Verify cascade: only USDA was called
        assert len(usda.called_with) == 1
        assert len(category.called_with) == 0
        assert len(fallback.called_with) == 0

    @pytest.mark.asyncio
    async def test_falls_back_to_category_if_usda_fails(self) -> None:
        """Test that category provider is used if USDA fails."""
        category_profile = NutrientProfile(
            calories=150,
            protein=25.0,
            carbs=5.0,
            fat=5.0,
            source="CATEGORY",
            confidence=0.7,
            quantity_g=100.0,
        )

        usda = MockUSDAProvider(return_value=None)  # USDA returns None
        category = MockCategoryProvider(return_value=category_profile)
        fallback = MockFallbackProvider()

        service = NutritionEnrichmentService(usda, category, fallback)

        result = await service.enrich("chicken", 100.0, "meat")

        # Should use category
        assert result.calories == 150
        assert result.source == "CATEGORY"

        # Verify cascade: USDA tried, then category
        assert len(usda.called_with) == 1
        assert len(category.called_with) == 1
        assert len(fallback.called_with) == 0

    @pytest.mark.asyncio
    async def test_falls_back_to_generic_if_all_fail(self) -> None:
        """Test that fallback provider is used if USDA and category fail."""
        usda = MockUSDAProvider(return_value=None)
        category = MockCategoryProvider(return_value=None)
        fallback = MockFallbackProvider()

        service = NutritionEnrichmentService(usda, category, fallback)

        result = await service.enrich("unknown food", 100.0, "unknown")

        # Should use fallback
        assert result.source == "AI_ESTIMATE"
        assert result.confidence == 0.3

        # Verify cascade: all three tried
        assert len(usda.called_with) == 1
        assert len(category.called_with) == 1
        assert len(fallback.called_with) == 1

    @pytest.mark.asyncio
    async def test_handles_usda_exception(self) -> None:
        """Test that exceptions from USDA are handled gracefully."""
        category_profile = NutrientProfile(
            calories=150,
            protein=25.0,
            carbs=5.0,
            fat=5.0,
            source="CATEGORY",
            confidence=0.7,
            quantity_g=100.0,
        )

        usda = MockUSDAProvider(should_raise=True)  # Raises exception
        category = MockCategoryProvider(return_value=category_profile)
        fallback = MockFallbackProvider()

        service = NutritionEnrichmentService(usda, category, fallback)

        result = await service.enrich("chicken", 100.0, "meat")

        # Should fall back to category despite exception
        assert result.source == "CATEGORY"

    @pytest.mark.asyncio
    async def test_handles_category_exception(self) -> None:
        """Test that exceptions from category are handled gracefully."""
        usda = MockUSDAProvider(return_value=None)
        category = MockCategoryProvider(should_raise=True)  # Raises exception
        fallback = MockFallbackProvider()

        service = NutritionEnrichmentService(usda, category, fallback)

        result = await service.enrich("chicken", 100.0, "meat")

        # Should fall back to generic despite exception
        assert result.source == "AI_ESTIMATE"

    @pytest.mark.asyncio
    async def test_skips_category_if_no_category_provided(self) -> None:
        """Test that category provider is skipped if no category given."""
        usda = MockUSDAProvider(return_value=None)
        category = MockCategoryProvider()
        fallback = MockFallbackProvider()

        service = NutritionEnrichmentService(usda, category, fallback)

        result = await service.enrich("unknown food", 100.0)  # No category

        # Should skip category and go to fallback
        assert result.source == "AI_ESTIMATE"

        # Verify category was NOT called
        assert len(usda.called_with) == 1
        assert len(category.called_with) == 0
        assert len(fallback.called_with) == 1

    @pytest.mark.asyncio
    async def test_raises_if_quantity_not_positive(self) -> None:
        """Test that non-positive quantity raises ValueError."""
        usda = MockUSDAProvider()
        category = MockCategoryProvider()
        fallback = MockFallbackProvider()

        service = NutritionEnrichmentService(usda, category, fallback)

        with pytest.raises(ValueError, match="Quantity must be positive"):
            await service.enrich("chicken", 0.0)

        with pytest.raises(ValueError, match="Quantity must be positive"):
            await service.enrich("chicken", -10.0)


class TestEnrichmentServiceScaling:
    """Test suite for quantity scaling."""

    @pytest.mark.asyncio
    async def test_scales_result_to_requested_quantity(self) -> None:
        """Test that result is scaled to requested quantity."""
        usda_profile = NutrientProfile(
            calories=100,
            protein=10.0,
            carbs=20.0,
            fat=2.0,
            quantity_g=100.0,
        )

        usda = MockUSDAProvider(return_value=usda_profile)
        category = MockCategoryProvider()
        fallback = MockFallbackProvider()

        service = NutritionEnrichmentService(usda, category, fallback)

        result = await service.enrich("test food", 250.0)

        # Should be scaled to 250g (2.5x)
        assert result.calories == 250  # 100 * 2.5
        assert result.protein == 25.0  # 10 * 2.5
        assert result.quantity_g == 250.0

    @pytest.mark.asyncio
    async def test_providers_called_with_100g_reference(self) -> None:
        """Test that providers are always called with 100g reference."""
        usda_profile = NutrientProfile(
            calories=100,
            protein=10.0,
            carbs=20.0,
            fat=2.0,
            quantity_g=100.0,
        )

        usda = MockUSDAProvider(return_value=usda_profile)
        category = MockCategoryProvider()
        fallback = MockFallbackProvider()

        service = NutritionEnrichmentService(usda, category, fallback)

        await service.enrich("test food", 350.0)

        # USDA should be called with 100.0 (reference quantity)
        assert usda.called_with[0] == ("test food", 100.0)


class TestEnrichmentServiceFallbackEdgeCases:
    """Test suite for fallback edge cases."""

    @pytest.mark.asyncio
    async def test_handles_fallback_returning_none(self) -> None:
        """Test graceful handling when fallback returns None."""

        class BrokenFallbackProvider:
            """Fallback that violates contract by returning None."""

            async def get_nutrients(
                self, identifier: str, quantity_g: float
            ) -> Optional[NutrientProfile]:
                return None  # Contract violation

        usda = MockUSDAProvider(return_value=None)
        category = MockCategoryProvider(return_value=None)
        fallback = BrokenFallbackProvider()

        service = NutritionEnrichmentService(usda, category, fallback)

        result = await service.enrich("unknown", 100.0)

        # Should return minimal profile as safety net
        assert result.calories == 100
        assert result.protein == 5.0
        assert result.carbs == 15.0
        assert result.fat == 3.0
        assert result.source == "AI_ESTIMATE"
        assert result.confidence == 0.3


class TestEnrichBatch:
    """Test suite for enrich_batch method."""

    @pytest.mark.asyncio
    async def test_enriches_multiple_items(self) -> None:
        """Test enriching multiple items in batch."""
        usda_profile_1 = NutrientProfile(
            calories=165,
            protein=31.0,
            carbs=0.0,
            fat=3.6,
            source="USDA",
            confidence=0.95,
            quantity_g=100.0,
        )

        usda_profile_2 = NutrientProfile(
            calories=130,
            protein=2.7,
            carbs=28.0,
            fat=0.3,
            source="USDA",
            confidence=0.9,
            quantity_g=100.0,
        )

        # Mock USDA to return different profiles based on label
        class SmartUSDAProvider:
            def __init__(self) -> None:
                self.called_count = 0

            async def get_nutrients(
                self, identifier: str, quantity_g: float
            ) -> Optional[NutrientProfile]:
                self.called_count += 1
                if "chicken" in identifier:
                    return usda_profile_1
                elif "rice" in identifier:
                    return usda_profile_2
                return None

        usda = SmartUSDAProvider()
        category = MockCategoryProvider()
        fallback = MockFallbackProvider()

        service = NutritionEnrichmentService(usda, category, fallback)

        items: list[tuple[str, float, Optional[str]]] = [
            ("chicken breast", 150.0, "meat"),
            ("rice", 200.0, "grains"),
        ]

        results = await service.enrich_batch(items)

        assert len(results) == 2

        # First item (chicken, scaled to 150g)
        assert results[0].calories == 247  # 165 * 1.5
        assert results[0].protein == 46.5

        # Second item (rice, scaled to 200g)
        assert results[1].calories == 260  # 130 * 2
        assert results[1].protein == 5.4  # 2.7 * 2

    @pytest.mark.asyncio
    async def test_returns_results_in_same_order(self) -> None:
        """Test that results are in same order as input."""
        usda = MockUSDAProvider()
        category = MockCategoryProvider()
        fallback = MockFallbackProvider()

        service = NutritionEnrichmentService(usda, category, fallback)

        items: list[tuple[str, float, Optional[str]]] = [
            ("food_a", 100.0, None),
            ("food_b", 200.0, None),
            ("food_c", 150.0, None),
        ]

        results = await service.enrich_batch(items)

        assert len(results) == 3
        # All use fallback with same base, but different quantities
        assert results[0].quantity_g == 100.0
        assert results[1].quantity_g == 200.0
        assert results[2].quantity_g == 150.0
