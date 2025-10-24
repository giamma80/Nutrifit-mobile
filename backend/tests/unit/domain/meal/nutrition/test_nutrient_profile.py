"""Unit tests for NutrientProfile entity.

Tests validation, scaling, and business logic methods.
"""

import pytest

from domain.meal.nutrition.entities import NutrientProfile


class TestNutrientProfileCreation:
    """Test suite for NutrientProfile creation and validation."""

    def test_creates_profile_with_required_fields(self) -> None:
        """Test creating profile with required macronutrients."""
        profile = NutrientProfile(
            calories=200,
            protein=10.0,
            carbs=30.0,
            fat=5.0,
        )

        assert profile.calories == 200
        assert profile.protein == 10.0
        assert profile.carbs == 30.0
        assert profile.fat == 5.0
        assert profile.quantity_g == 100.0  # Default
        assert profile.source == "USDA"  # Default
        assert profile.confidence == 0.9  # Default

    def test_creates_profile_with_optional_micronutrients(self) -> None:
        """Test creating profile with optional micronutrients."""
        profile = NutrientProfile(
            calories=200,
            protein=10.0,
            carbs=30.0,
            fat=5.0,
            fiber=3.0,
            sugar=10.0,
            sodium=150.0,
        )

        assert profile.fiber == 3.0
        assert profile.sugar == 10.0
        assert profile.sodium == 150.0

    def test_creates_profile_with_custom_metadata(self) -> None:
        """Test creating profile with custom source and confidence."""
        profile = NutrientProfile(
            calories=200,
            protein=10.0,
            carbs=30.0,
            fat=5.0,
            source="BARCODE_DB",
            confidence=0.95,
            quantity_g=150.0,
        )

        assert profile.source == "BARCODE_DB"
        assert profile.confidence == 0.95
        assert profile.quantity_g == 150.0

    def test_raises_if_quantity_not_positive(self) -> None:
        """Test that non-positive quantity raises ValueError."""
        with pytest.raises(ValueError, match="Quantity must be positive"):
            NutrientProfile(
                calories=200,
                protein=10.0,
                carbs=30.0,
                fat=5.0,
                quantity_g=0.0,
            )

        with pytest.raises(ValueError, match="Quantity must be positive"):
            NutrientProfile(
                calories=200,
                protein=10.0,
                carbs=30.0,
                fat=5.0,
                quantity_g=-10.0,
            )

    def test_raises_if_confidence_out_of_range(self) -> None:
        """Test that confidence outside [0, 1] raises ValueError."""
        with pytest.raises(ValueError, match="Confidence must be between"):
            NutrientProfile(
                calories=200,
                protein=10.0,
                carbs=30.0,
                fat=5.0,
                confidence=-0.1,
            )

        with pytest.raises(ValueError, match="Confidence must be between"):
            NutrientProfile(
                calories=200,
                protein=10.0,
                carbs=30.0,
                fat=5.0,
                confidence=1.5,
            )

    def test_raises_if_calories_negative(self) -> None:
        """Test that negative calories raise ValueError."""
        with pytest.raises(ValueError, match="Calories cannot be negative"):
            NutrientProfile(
                calories=-100,
                protein=10.0,
                carbs=30.0,
                fat=5.0,
            )

    def test_raises_if_macros_negative(self) -> None:
        """Test that negative macronutrients raise ValueError."""
        with pytest.raises(ValueError, match="Protein cannot be negative"):
            NutrientProfile(calories=200, protein=-10.0, carbs=30.0, fat=5.0)

        with pytest.raises(ValueError, match="Carbs cannot be negative"):
            NutrientProfile(calories=200, protein=10.0, carbs=-30.0, fat=5.0)

        with pytest.raises(ValueError, match="Fat cannot be negative"):
            NutrientProfile(calories=200, protein=10.0, carbs=30.0, fat=-5.0)


class TestScaleToQuantity:
    """Test suite for scale_to_quantity method."""

    def test_scales_to_larger_quantity(self) -> None:
        """Test scaling from 100g to 150g."""
        profile = NutrientProfile(
            calories=200,
            protein=10.0,
            carbs=30.0,
            fat=5.0,
            quantity_g=100.0,
        )

        scaled = profile.scale_to_quantity(150.0)

        assert scaled.calories == 300  # 200 * 1.5
        assert scaled.protein == 15.0  # 10 * 1.5
        assert scaled.carbs == 45.0  # 30 * 1.5
        assert scaled.fat == 7.5  # 5 * 1.5
        assert scaled.quantity_g == 150.0

    def test_scales_to_smaller_quantity(self) -> None:
        """Test scaling from 100g to 50g."""
        profile = NutrientProfile(
            calories=200,
            protein=10.0,
            carbs=30.0,
            fat=5.0,
            quantity_g=100.0,
        )

        scaled = profile.scale_to_quantity(50.0)

        assert scaled.calories == 100  # 200 * 0.5
        assert scaled.protein == 5.0  # 10 * 0.5
        assert scaled.carbs == 15.0  # 30 * 0.5
        assert scaled.fat == 2.5  # 5 * 0.5
        assert scaled.quantity_g == 50.0

    def test_scales_micronutrients(self) -> None:
        """Test that micronutrients are also scaled."""
        profile = NutrientProfile(
            calories=200,
            protein=10.0,
            carbs=30.0,
            fat=5.0,
            fiber=3.0,
            sugar=10.0,
            sodium=150.0,
            quantity_g=100.0,
        )

        scaled = profile.scale_to_quantity(200.0)

        assert scaled.fiber == 6.0  # 3 * 2
        assert scaled.sugar == 20.0  # 10 * 2
        assert scaled.sodium == 300.0  # 150 * 2

    def test_preserves_metadata(self) -> None:
        """Test that source and confidence are preserved during scaling."""
        profile = NutrientProfile(
            calories=200,
            protein=10.0,
            carbs=30.0,
            fat=5.0,
            source="BARCODE_DB",
            confidence=0.95,
        )

        scaled = profile.scale_to_quantity(150.0)

        assert scaled.source == "BARCODE_DB"
        assert scaled.confidence == 0.95

    def test_original_unchanged_after_scaling(self) -> None:
        """Test that scaling creates new instance, original unchanged."""
        profile = NutrientProfile(
            calories=200,
            protein=10.0,
            carbs=30.0,
            fat=5.0,
            quantity_g=100.0,
        )

        _ = profile.scale_to_quantity(150.0)

        # Original should be unchanged
        assert profile.calories == 200
        assert profile.quantity_g == 100.0

    def test_raises_if_target_not_positive(self) -> None:
        """Test that non-positive target quantity raises ValueError."""
        profile = NutrientProfile(
            calories=200,
            protein=10.0,
            carbs=30.0,
            fat=5.0,
        )

        with pytest.raises(ValueError, match="Target quantity must be positive"):
            profile.scale_to_quantity(0.0)

        with pytest.raises(ValueError, match="Target quantity must be positive"):
            profile.scale_to_quantity(-10.0)


class TestCaloriesFromMacros:
    """Test suite for calories_from_macros method."""

    def test_calculates_calories_4_4_9_rule(self) -> None:
        """Test calories calculation using Atwater 4-4-9 rule."""
        profile = NutrientProfile(
            calories=205,  # Declared (may differ)
            protein=10.0,  # 10 * 4 = 40 kcal
            carbs=30.0,  # 30 * 4 = 120 kcal
            fat=5.0,  # 5 * 9 = 45 kcal
        )

        calculated = profile.calories_from_macros()

        assert calculated == 205  # 40 + 120 + 45

    def test_handles_zero_macros(self) -> None:
        """Test calories calculation with zero macros."""
        profile = NutrientProfile(
            calories=0,
            protein=0.0,
            carbs=0.0,
            fat=0.0,
        )

        calculated = profile.calories_from_macros()

        assert calculated == 0

    def test_rounds_to_integer(self) -> None:
        """Test that result is rounded to integer."""
        profile = NutrientProfile(
            calories=100,
            protein=5.5,  # 22 kcal
            carbs=10.5,  # 42 kcal
            fat=2.2,  # 19.8 kcal
        )

        calculated = profile.calories_from_macros()

        assert isinstance(calculated, int)
        assert calculated == 83  # int(22 + 42 + 19.8)


class TestIsHighQuality:
    """Test suite for is_high_quality method."""

    def test_usda_with_high_confidence_is_high_quality(self) -> None:
        """Test that USDA source with confidence > 0.8 is high quality."""
        profile = NutrientProfile(
            calories=200,
            protein=10.0,
            carbs=30.0,
            fat=5.0,
            source="USDA",
            confidence=0.95,
        )

        assert profile.is_high_quality() is True

    def test_barcode_with_high_confidence_is_high_quality(self) -> None:
        """Test that BARCODE_DB with confidence > 0.8 is high quality."""
        profile = NutrientProfile(
            calories=200,
            protein=10.0,
            carbs=30.0,
            fat=5.0,
            source="BARCODE_DB",
            confidence=0.85,
        )

        assert profile.is_high_quality() is True

    def test_usda_with_low_confidence_is_not_high_quality(self) -> None:
        """Test that USDA with confidence <= 0.8 is not high quality."""
        profile = NutrientProfile(
            calories=200,
            protein=10.0,
            carbs=30.0,
            fat=5.0,
            source="USDA",
            confidence=0.75,
        )

        assert profile.is_high_quality() is False

    def test_category_source_is_not_high_quality(self) -> None:
        """Test that CATEGORY source is not high quality."""
        profile = NutrientProfile(
            calories=200,
            protein=10.0,
            carbs=30.0,
            fat=5.0,
            source="CATEGORY",
            confidence=0.95,
        )

        assert profile.is_high_quality() is False

    def test_ai_estimate_is_not_high_quality(self) -> None:
        """Test that AI_ESTIMATE is not high quality."""
        profile = NutrientProfile(
            calories=200,
            protein=10.0,
            carbs=30.0,
            fat=5.0,
            source="AI_ESTIMATE",
            confidence=0.95,
        )

        assert profile.is_high_quality() is False


class TestNutrientProfileEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_accepts_zero_calories(self) -> None:
        """Test that zero calories is valid (e.g., water, tea)."""
        profile = NutrientProfile(
            calories=0,
            protein=0.0,
            carbs=0.0,
            fat=0.0,
        )
        assert profile.calories == 0

    def test_accepts_zero_macros_individually(self) -> None:
        """Test zero values for individual macros."""
        profile = NutrientProfile(
            calories=100,
            protein=0.0,  # Fat-free lean meat edge case
            carbs=25.0,
            fat=0.0,  # Fat-free product
        )
        assert profile.protein == 0.0
        assert profile.fat == 0.0

    def test_scale_to_same_quantity_returns_equal_profile(self) -> None:
        """Test scaling to same quantity returns equivalent profile."""
        profile = NutrientProfile(
            calories=200,
            protein=10.0,
            carbs=30.0,
            fat=5.0,
            quantity_g=100.0,
        )

        scaled = profile.scale_to_quantity(100.0)

        assert scaled.calories == 200
        assert scaled.protein == 10.0
        assert scaled.quantity_g == 100.0

    def test_accepts_confidence_boundary_values(self) -> None:
        """Test confidence boundaries at 0.0 and 1.0."""
        profile_zero = NutrientProfile(
            calories=200,
            protein=10.0,
            carbs=30.0,
            fat=5.0,
            confidence=0.0,
        )
        assert profile_zero.confidence == 0.0

        profile_one = NutrientProfile(
            calories=200,
            protein=10.0,
            carbs=30.0,
            fat=5.0,
            confidence=1.0,
        )
        assert profile_one.confidence == 1.0

    def test_source_variants(self) -> None:
        """Test all valid source values."""
        sources = ["USDA", "BARCODE_DB", "CATEGORY", "AI_ESTIMATE"]

        for source in sources:
            profile = NutrientProfile(
                calories=200,
                protein=10.0,
                carbs=30.0,
                fat=5.0,
                source=source,  # type: ignore
            )
            assert profile.source == source

    def test_very_small_quantity_scaling(self) -> None:
        """Test scaling to very small quantities (e.g., spices, salt)."""
        profile = NutrientProfile(
            calories=300,
            protein=10.0,
            carbs=50.0,
            fat=5.0,
            quantity_g=100.0,
        )

        # Scale to 1g (e.g., salt, pepper)
        scaled = profile.scale_to_quantity(1.0)

        assert scaled.calories == 3  # int(300 * 0.01)
        assert pytest.approx(scaled.protein, abs=0.01) == 0.1
        assert scaled.quantity_g == 1.0

    def test_very_large_quantity_scaling(self) -> None:
        """Test scaling to large quantities (e.g., meal prep)."""
        profile = NutrientProfile(
            calories=100,
            protein=20.0,
            carbs=5.0,
            fat=2.0,
            quantity_g=100.0,
        )

        # Scale to 1kg
        scaled = profile.scale_to_quantity(1000.0)

        assert scaled.calories == 1000  # 100 * 10
        assert scaled.protein == 200.0  # 20 * 10
        assert scaled.quantity_g == 1000.0


class TestMacroDistribution:
    """Test suite for macro_distribution method."""

    def test_calculates_distribution_percentages(self) -> None:
        """Test macro distribution calculation."""
        profile = NutrientProfile(
            calories=205,
            protein=10.0,  # 40 kcal (19.5%)
            carbs=30.0,  # 120 kcal (58.5%)
            fat=5.0,  # 45 kcal (22.0%)
        )

        dist = profile.macro_distribution()

        # Allow small floating point variance
        assert pytest.approx(dist["protein_pct"], abs=0.1) == 19.5
        assert pytest.approx(dist["carbs_pct"], abs=0.1) == 58.5
        assert pytest.approx(dist["fat_pct"], abs=0.1) == 22.0

    def test_handles_zero_calories(self) -> None:
        """Test distribution with zero calories."""
        profile = NutrientProfile(
            calories=0,
            protein=0.0,
            carbs=0.0,
            fat=0.0,
        )

        dist = profile.macro_distribution()

        assert dist["protein_pct"] == 0.0
        assert dist["carbs_pct"] == 0.0
        assert dist["fat_pct"] == 0.0

    def test_percentages_sum_to_100(self) -> None:
        """Test that percentages sum to approximately 100%."""
        profile = NutrientProfile(
            calories=300,
            protein=20.0,  # 80 kcal
            carbs=40.0,  # 160 kcal
            fat=10.0,  # 90 kcal
        )

        dist = profile.macro_distribution()

        total = dist["protein_pct"] + dist["carbs_pct"] + dist["fat_pct"]

        assert pytest.approx(total, abs=0.1) == 100.0
