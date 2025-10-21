"""
USDA data mapper.

Transforms USDA API responses to domain models.
"""

from typing import Any

from backend.v2.domain.meal.nutrition.models import (
    NutrientProfile,
    NutrientSource,
)
from backend.v2.domain.meal.nutrition.usda_models import (
    USDAFoodItem,
    USDANutrient,
    USDASearchResult,
)


class USDAMapper:
    """Maps USDA API data to domain models."""

    # USDA nutrient number mappings
    NUTRIENT_MAP = {
        "208": "calories",  # Energy (kcal)
        "203": "protein",  # Protein (g)
        "205": "carbs",  # Carbohydrate (g)
        "204": "fat",  # Total lipid (fat) (g)
        "291": "fiber",  # Fiber, total dietary (g)
        "269": "sugar",  # Sugars, total (g)
        "307": "sodium",  # Sodium (mg)
    }

    @staticmethod
    def map_nutrients_to_dict(
        nutrients: list[USDANutrient],
    ) -> dict[str, float]:
        """Convert USDA nutrients to dict.

        Args:
            nutrients: List of USDA nutrients

        Returns:
            Dictionary with nutrient values per 100g

        Example:
            >>> nutrients = [
            ...     USDANutrient(
            ...         number="208",
            ...         name="Energy",
            ...         amount=52.0,
            ...         unit="kcal",
            ...     ),
            ...     USDANutrient(
            ...         number="203",
            ...         name="Protein",
            ...         amount=0.3,
            ...         unit="g",
            ...     ),
            ... ]
            >>> result = USDAMapper.map_nutrients_to_dict(nutrients)
            >>> assert result["calories"] == 52.0
            >>> assert result["protein"] == 0.3
        """
        nutrient_dict: dict[str, float] = {}

        for nutrient in nutrients:
            field_name = USDAMapper.NUTRIENT_MAP.get(nutrient.number)
            if field_name:
                nutrient_dict[field_name] = nutrient.amount

        return nutrient_dict

    @staticmethod
    def to_nutrient_profile(food_item: USDAFoodItem) -> NutrientProfile:
        """Convert USDA food item to NutrientProfile.

        Args:
            food_item: USDA food item

        Returns:
            Domain NutrientProfile

        Example:
            >>> from backend.v2.domain.meal.nutrition.usda_models import (
            ...     USDADataType,
            ...     USDAFoodItem,
            ... )
            >>> food = USDAFoodItem(
            ...     fdc_id="123",
            ...     description="Apple, raw",
            ...     data_type=USDADataType.SR_LEGACY,
            ...     nutrients=[
            ...         USDANutrient(
            ...             number="208",
            ...             name="Energy",
            ...             amount=52.0,
            ...             unit="kcal",
            ...         ),
            ...         USDANutrient(
            ...             number="203",
            ...             name="Protein",
            ...             amount=0.3,
            ...             unit="g",
            ...         ),
            ...     ],
            ... )
            >>> profile = USDAMapper.to_nutrient_profile(food)
            >>> assert profile.calories == 52.0
            >>> assert profile.source == NutrientSource.USDA
        """
        nutrient_dict = USDAMapper.map_nutrients_to_dict(food_item.nutrients)

        return NutrientProfile(
            calories=nutrient_dict.get("calories", 0.0),
            protein=nutrient_dict.get("protein", 0.0),
            carbs=nutrient_dict.get("carbs", 0.0),
            fat=nutrient_dict.get("fat", 0.0),
            fiber=nutrient_dict.get("fiber"),
            sugar=nutrient_dict.get("sugar"),
            sodium=nutrient_dict.get("sodium"),
            source=NutrientSource.USDA,
            confidence=0.95,  # USDA is high-quality verified data
        )

    @staticmethod
    def parse_search_response(response_data: dict[str, Any]) -> USDASearchResult:
        """Parse USDA search API response.

        Args:
            response_data: Raw API response JSON

        Returns:
            Parsed USDASearchResult

        Example:
            >>> response = {
            ...     "totalHits": 1,
            ...     "currentPage": 1,
            ...     "totalPages": 1,
            ...     "foods": [
            ...         {
            ...             "fdcId": 123,
            ...             "description": "Apple, raw",
            ...             "dataType": "SR Legacy",
            ...             "foodNutrients": [
            ...                 {
            ...                     "nutrientNumber": "208",
            ...                     "nutrientName": "Energy",
            ...                     "value": 52.0,
            ...                     "unitName": "kcal",
            ...                 }
            ...             ],
            ...         }
            ...     ],
            ... }
            >>> result = USDAMapper.parse_search_response(response)
            >>> assert result.total_hits == 1
            >>> assert len(result.foods) == 1
        """
        foods = []
        for food_data in response_data.get("foods", []):
            nutrients = []
            for n in food_data.get("foodNutrients", []):
                nutrients.append(
                    USDANutrient(
                        number=str(n.get("nutrientNumber", "")),
                        name=n.get("nutrientName", ""),
                        amount=float(n.get("value", 0.0)),
                        unit=n.get("unitName", ""),
                    )
                )

            foods.append(
                USDAFoodItem(
                    fdc_id=str(food_data.get("fdcId", "")),
                    description=food_data.get("description", ""),
                    data_type=food_data.get("dataType", "SR Legacy"),
                    nutrients=nutrients,
                    brand_owner=food_data.get("brandOwner"),
                    gtin_upc=food_data.get("gtinUpc"),
                )
            )

        return USDASearchResult(
            total_hits=response_data.get("totalHits", 0),
            current_page=response_data.get("currentPage", 1),
            total_pages=response_data.get("totalPages", 0),
            foods=foods,
        )
