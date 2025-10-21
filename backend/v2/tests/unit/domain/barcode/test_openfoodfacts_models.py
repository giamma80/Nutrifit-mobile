"""
Unit tests for OpenFoodFacts domain models.
"""

import pytest

from backend.v2.domain.meal.barcode.openfoodfacts_models import (
    BarcodeQuality,
    NovaGroup,
    NutriscoreGrade,
    OFFNutriments,
    OFFProduct,
    OFFSearchResult,
)


class TestOFFNutriments:
    """Test OFFNutriments model."""

    def test_create_complete_nutriments(self) -> None:
        """Should create complete nutriments."""
        nutriments = OFFNutriments(
            energy_kcal=539.0,
            proteins=6.3,
            carbohydrates=57.5,
            fat=30.9,
            fiber=0.0,
            sugars=56.3,
            sodium=0.107,
            salt=0.27,
        )

        assert nutriments.energy_kcal == 539.0
        assert nutriments.proteins == 6.3
        assert nutriments.carbohydrates == 57.5
        assert nutriments.fat == 30.9

    def test_create_partial_nutriments(self) -> None:
        """Should handle optional nutrients."""
        nutriments = OFFNutriments(
            energy_kcal=100.0,
            proteins=5.0,
        )

        assert nutriments.energy_kcal == 100.0
        assert nutriments.proteins == 5.0
        assert nutriments.carbohydrates is None
        assert nutriments.fat is None

    def test_reject_negative_values(self) -> None:
        """Should reject negative values."""
        with pytest.raises(ValueError):
            OFFNutriments(
                energy_kcal=-100.0,
                proteins=5.0,
            )

    def test_nutriments_is_immutable(self) -> None:
        """Should be immutable."""
        nutriments = OFFNutriments(energy_kcal=100.0, proteins=5.0)

        with pytest.raises(Exception):
            nutriments.energy_kcal = 200.0  # noqa: SLF001


class TestOFFProduct:
    """Test OFFProduct model."""

    def test_create_minimal_product(self) -> None:
        """Should create minimal product."""
        product = OFFProduct(code="3017620422003")

        assert product.code == "3017620422003"
        assert product.product_name is None
        assert product.brands is None

    def test_create_complete_product(self) -> None:
        """Should create complete product."""
        nutriments = OFFNutriments(
            energy_kcal=539.0,
            proteins=6.3,
            carbohydrates=57.5,
            fat=30.9,
        )

        product = OFFProduct(
            code="3017620422003",
            product_name="Nutella",
            brands="Ferrero",
            categories="Spreads",
            quantity="750g",
            serving_size="15g",
            image_url="https://example.com/image.jpg",
            nutriments=nutriments,
            nutriscore_grade=NutriscoreGrade.E,
            nova_group=NovaGroup.GROUP_4,
            ingredients_text="Sugar, palm oil, hazelnuts",
            allergens="nuts",
        )

        assert product.code == "3017620422003"
        assert product.product_name == "Nutella"
        assert product.brands == "Ferrero"
        assert product.nutriscore_grade == NutriscoreGrade.E
        assert product.nova_group == NovaGroup.GROUP_4

    def test_product_is_immutable(self) -> None:
        """Should be immutable."""
        product = OFFProduct(code="123")

        with pytest.raises(Exception):
            product.product_name = "Test"  # noqa: SLF001


class TestOFFSearchResult:
    """Test OFFSearchResult model."""

    def test_product_found(self) -> None:
        """Should indicate product found."""
        product = OFFProduct(
            code="3017620422003",
            product_name="Nutella",
        )

        result = OFFSearchResult(status=1, product=product)

        assert result.status == 1
        assert result.product is not None
        assert result.is_found() is True

    def test_product_not_found(self) -> None:
        """Should indicate product not found."""
        result = OFFSearchResult(status=0, product=None)

        assert result.status == 0
        assert result.product is None
        assert result.is_found() is False

    def test_status_1_but_no_product(self) -> None:
        """Should handle edge case of status=1 but no product."""
        result = OFFSearchResult(status=1, product=None)

        assert result.is_found() is False


class TestBarcodeQuality:
    """Test BarcodeQuality model."""

    def test_create_quality_metrics(self) -> None:
        """Should create quality metrics."""
        quality = BarcodeQuality(
            completeness=0.85,
            source_reliability=0.90,
            data_freshness=0.95,
        )

        assert quality.completeness == 0.85
        assert quality.source_reliability == 0.90
        assert quality.data_freshness == 0.95

    def test_overall_score_calculation(self) -> None:
        """Should calculate overall score correctly."""
        quality = BarcodeQuality(
            completeness=1.0,
            source_reliability=1.0,
            data_freshness=1.0,
        )

        score = quality.overall_score()
        assert score == 1.0

    def test_weighted_score(self) -> None:
        """Should use weighted average."""
        quality = BarcodeQuality(
            completeness=0.8,  # 40% weight
            source_reliability=0.9,  # 40% weight
            data_freshness=0.5,  # 20% weight
        )

        # (0.8 * 0.4) + (0.9 * 0.4) + (0.5 * 0.2) = 0.78
        score = quality.overall_score()
        assert score == 0.78

    def test_reject_out_of_range(self) -> None:
        """Should reject values out of range."""
        with pytest.raises(ValueError):
            BarcodeQuality(
                completeness=1.5,
                source_reliability=0.9,
                data_freshness=0.8,
            )

    def test_quality_is_immutable(self) -> None:
        """Should be immutable."""
        quality = BarcodeQuality(
            completeness=0.8,
            source_reliability=0.9,
            data_freshness=0.95,
        )

        with pytest.raises(Exception):
            quality.completeness = 1.0  # noqa: SLF001


class TestNutriscoreGrade:
    """Test NutriscoreGrade enum."""

    def test_all_grades_available(self) -> None:
        """Should have all Nutriscore grades."""
        assert NutriscoreGrade.A.value == "a"
        assert NutriscoreGrade.B.value == "b"
        assert NutriscoreGrade.C.value == "c"
        assert NutriscoreGrade.D.value == "d"
        assert NutriscoreGrade.E.value == "e"
        assert NutriscoreGrade.UNKNOWN.value == "unknown"


class TestNovaGroup:
    """Test NovaGroup enum."""

    def test_all_groups_available(self) -> None:
        """Should have all NOVA groups."""
        assert NovaGroup.GROUP_1.value == "1"
        assert NovaGroup.GROUP_2.value == "2"
        assert NovaGroup.GROUP_3.value == "3"
        assert NovaGroup.GROUP_4.value == "4"
        assert NovaGroup.UNKNOWN.value == "unknown"
