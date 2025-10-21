"""
OpenFoodFacts data mapper.

Transforms OpenFoodFacts API responses to domain models.
"""

from typing import Any

from backend.v2.domain.meal.nutrition.models import (
    NutrientProfile,
    NutrientSource,
)
from backend.v2.domain.meal.barcode.openfoodfacts_models import (
    NovaGroup,
    NutriscoreGrade,
    OFFNutriments,
    OFFProduct,
    OFFSearchResult,
)


class OpenFoodFactsMapper:
    """Maps OpenFoodFacts API data to domain models."""

    @staticmethod
    def parse_product_response(response_data: dict[str, Any]) -> OFFSearchResult:
        """Parse OpenFoodFacts product API response.

        Args:
            response_data: Raw API response JSON

        Returns:
            Parsed OFFSearchResult

        Example:
            >>> response = {
            ...     "status": 1,
            ...     "product": {
            ...         "code": "3017620422003",
            ...         "product_name": "Nutella",
            ...         "brands": "Ferrero",
            ...         "nutriments": {
            ...             "energy-kcal_100g": 539.0,
            ...             "proteins_100g": 6.3,
            ...             "carbohydrates_100g": 57.5,
            ...             "fat_100g": 30.9,
            ...         },
            ...     },
            ... }
            >>> result = OpenFoodFactsMapper.parse_product_response(
            ...     response
            ... )
            >>> assert result.status == 1
            >>> assert result.product.product_name == "Nutella"
        """
        status = response_data.get("status", 0)

        if status == 0 or "product" not in response_data:
            return OFFSearchResult(status=status, product=None)

        product_data = response_data["product"]
        nutriments_data = product_data.get("nutriments", {})

        # Parse nutriments
        nutriments = OFFNutriments(
            energy_kcal=nutriments_data.get("energy-kcal_100g"),
            proteins=nutriments_data.get("proteins_100g"),
            carbohydrates=nutriments_data.get("carbohydrates_100g"),
            fat=nutriments_data.get("fat_100g"),
            fiber=nutriments_data.get("fiber_100g"),
            sugars=nutriments_data.get("sugars_100g"),
            sodium=nutriments_data.get("sodium_100g"),
            salt=nutriments_data.get("salt_100g"),
        )

        # Parse nutriscore
        nutriscore_raw = product_data.get("nutriscore_grade")
        nutriscore = None
        if nutriscore_raw:
            try:
                nutriscore = NutriscoreGrade(nutriscore_raw.lower())
            except ValueError:
                nutriscore = NutriscoreGrade.UNKNOWN

        # Parse nova group
        nova_raw = product_data.get("nova_group")
        nova = None
        if nova_raw:
            try:
                nova = NovaGroup(str(nova_raw))
            except ValueError:
                nova = NovaGroup.UNKNOWN

        # Create product
        product = OFFProduct(
            code=product_data.get("code", ""),
            product_name=product_data.get("product_name"),
            brands=product_data.get("brands"),
            categories=product_data.get("categories"),
            quantity=product_data.get("quantity"),
            serving_size=product_data.get("serving_size"),
            image_url=product_data.get("image_url"),
            nutriments=nutriments,
            nutriscore_grade=nutriscore,
            nova_group=nova,
            ingredients_text=product_data.get("ingredients_text"),
            allergens=product_data.get("allergens"),
        )

        return OFFSearchResult(status=status, product=product)

    @staticmethod
    def to_nutrient_profile(product: OFFProduct) -> NutrientProfile:
        """Convert OpenFoodFacts product to NutrientProfile.

        Args:
            product: OpenFoodFacts product

        Returns:
            Domain NutrientProfile

        Example:
            >>> product = OFFProduct(
            ...     code="3017620422003",
            ...     product_name="Nutella",
            ...     brands="Ferrero",
            ...     nutriments=OFFNutriments(
            ...         energy_kcal=539.0,
            ...         proteins=6.3,
            ...         carbohydrates=57.5,
            ...         fat=30.9,
            ...         fiber=0.0,
            ...         sugars=56.3,
            ...     ),
            ... )
            >>> profile = OpenFoodFactsMapper.to_nutrient_profile(
            ...     product
            ... )
            >>> assert profile.calories == 539.0
            >>> assert profile.source == NutrientSource.BARCODE_DB
        """
        n = product.nutriments if product.nutriments else OFFNutriments()

        # Convert sodium from mg to match our domain
        sodium = n.sodium if n.sodium is not None else None

        return NutrientProfile(
            calories=n.energy_kcal or 0.0,
            protein=n.proteins or 0.0,
            carbs=n.carbohydrates or 0.0,
            fat=n.fat or 0.0,
            fiber=n.fiber,
            sugar=n.sugars,
            sodium=sodium,
            source=NutrientSource.BARCODE_DB,
        )

    @staticmethod
    def calculate_completeness(product: OFFProduct) -> float:
        """Calculate data completeness score.

        Args:
            product: OpenFoodFacts product

        Returns:
            Completeness score (0-1)

        Example:
            >>> product = OFFProduct(
            ...     code="123",
            ...     product_name="Test",
            ...     brands="Brand",
            ...     nutriments=OFFNutriments(
            ...         energy_kcal=100.0,
            ...         proteins=5.0,
            ...         carbohydrates=10.0,
            ...         fat=2.0,
            ...     ),
            ... )
            >>> score = OpenFoodFactsMapper.calculate_completeness(
            ...     product
            ... )
            >>> assert 0.0 <= score <= 1.0
        """
        n = product.nutriments if product.nutriments else OFFNutriments()

        fields_to_check = [
            product.product_name,
            product.brands,
            n.energy_kcal,
            n.proteins,
            n.carbohydrates,
            n.fat,
            n.fiber,
            n.sugars,
            n.sodium,
        ]

        filled = sum(1 for field in fields_to_check if field is not None)
        return round(filled / len(fields_to_check), 2)
