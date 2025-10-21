"""
Unit tests for OpenFoodFacts mapper.
"""

from backend.v2.domain.meal.barcode.openfoodfacts_mapper import (
    OpenFoodFactsMapper,
)
from backend.v2.domain.meal.barcode.openfoodfacts_models import (
    NovaGroup,
    NutriscoreGrade,
    OFFNutriments,
    OFFProduct,
)
from backend.v2.domain.meal.nutrition.models import NutrientSource


class TestOpenFoodFactsMapper:
    """Test OpenFoodFacts data mapper."""

    def test_parse_complete_product_response(self) -> None:
        """Should parse complete product response."""
        response = {
            "status": 1,
            "product": {
                "code": "3017620422003",
                "product_name": "Nutella",
                "brands": "Ferrero",
                "categories": "Spreads",
                "quantity": "750g",
                "serving_size": "15g",
                "image_url": "https://example.com/image.jpg",
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
                "nutriscore_grade": "e",
                "nova_group": 4,
                "ingredients_text": "Sugar, palm oil, hazelnuts",
                "allergens": "nuts",
            },
        }

        result = OpenFoodFactsMapper.parse_product_response(response)

        assert result.status == 1
        assert result.product is not None
        assert result.product.code == "3017620422003"
        assert result.product.product_name == "Nutella"
        assert result.product.brands == "Ferrero"
        assert result.product.nutriscore_grade == NutriscoreGrade.E
        assert result.product.nova_group == NovaGroup.GROUP_4

    def test_parse_minimal_product_response(self) -> None:
        """Should parse minimal product response."""
        response = {
            "status": 1,
            "product": {
                "code": "123456789",
                "nutriments": {},
            },
        }

        result = OpenFoodFactsMapper.parse_product_response(response)

        assert result.status == 1
        assert result.product is not None
        assert result.product.code == "123456789"
        assert result.product.product_name is None

    def test_parse_not_found_response(self) -> None:
        """Should handle not found response."""
        response = {"status": 0}

        result = OpenFoodFactsMapper.parse_product_response(response)

        assert result.status == 0
        assert result.product is None
        assert result.is_found() is False

    def test_parse_invalid_nutriscore(self) -> None:
        """Should handle invalid nutriscore gracefully."""
        response = {
            "status": 1,
            "product": {
                "code": "123",
                "nutriscore_grade": "invalid",
                "nutriments": {},
            },
        }

        result = OpenFoodFactsMapper.parse_product_response(response)

        assert result.product is not None
        assert result.product.nutriscore_grade == NutriscoreGrade.UNKNOWN

    def test_parse_invalid_nova_group(self) -> None:
        """Should handle invalid NOVA group gracefully."""
        response = {
            "status": 1,
            "product": {
                "code": "123",
                "nova_group": 99,
                "nutriments": {},
            },
        }

        result = OpenFoodFactsMapper.parse_product_response(response)

        assert result.product is not None
        assert result.product.nova_group == NovaGroup.UNKNOWN

    def test_to_nutrient_profile(self) -> None:
        """Should convert to NutrientProfile."""
        product = OFFProduct(
            code="3017620422003",
            product_name="Nutella",
            brands="Ferrero",
            nutriments=OFFNutriments(
                energy_kcal=539.0,
                proteins=6.3,
                carbohydrates=57.5,
                fat=30.9,
                fiber=0.0,
                sugars=56.3,
                sodium=107.0,
            ),
        )

        profile = OpenFoodFactsMapper.to_nutrient_profile(product)

        assert profile.calories == 539.0
        assert profile.protein == 6.3
        assert profile.carbs == 57.5
        assert profile.fat == 30.9
        assert profile.fiber == 0.0
        assert profile.sugar == 56.3
        assert profile.sodium == 107.0
        assert profile.source == NutrientSource.BARCODE_DB

    def test_to_nutrient_profile_with_nulls(self) -> None:
        """Should handle null values in nutrients."""
        product = OFFProduct(
            code="123",
            nutriments=OFFNutriments(
                energy_kcal=100.0,
                proteins=5.0,
            ),
        )

        profile = OpenFoodFactsMapper.to_nutrient_profile(product)

        assert profile.calories == 100.0
        assert profile.protein == 5.0
        assert profile.carbs == 0.0  # Default to 0
        assert profile.fat == 0.0
        assert profile.fiber is None
        assert profile.sugar is None

    def test_calculate_completeness_full(self) -> None:
        """Should calculate 100% completeness."""
        product = OFFProduct(
            code="123",
            product_name="Test Product",
            brands="Test Brand",
            nutriments=OFFNutriments(
                energy_kcal=100.0,
                proteins=5.0,
                carbohydrates=10.0,
                fat=2.0,
                fiber=1.0,
                sugars=3.0,
                sodium=50.0,
            ),
        )

        completeness = OpenFoodFactsMapper.calculate_completeness(product)

        assert completeness == 1.0

    def test_calculate_completeness_partial(self) -> None:
        """Should calculate partial completeness."""
        product = OFFProduct(
            code="123",
            product_name="Test",
            nutriments=OFFNutriments(
                energy_kcal=100.0,
                proteins=5.0,
            ),
        )

        completeness = OpenFoodFactsMapper.calculate_completeness(product)

        # 3 fields filled out of 9
        assert completeness == 0.33

    def test_calculate_completeness_minimal(self) -> None:
        """Should handle minimal data."""
        product = OFFProduct(
            code="123",
            nutriments=OFFNutriments(),
        )

        completeness = OpenFoodFactsMapper.calculate_completeness(product)

        assert completeness == 0.0
