"""
Integration test for USDA enrichment - Banana analysis.

Tests complete flow: Search → Parse → Map → Profile
Example: 100g of banana nutritional analysis
"""

import pytest

from backend.v2.domain.meal.nutrition.usda_models import (
    USDAFoodItem,
    USDANutrient,
    USDASearchResult,
    USDADataType,
)
from backend.v2.domain.meal.nutrition.usda_mapper import USDAMapper
from backend.v2.domain.meal.nutrition.models import (
    NutrientProfile,
    NutrientSource,
)


class TestUSDABananaAnalysis:
    """Integration test for USDA banana nutritional analysis."""

    @pytest.fixture
    def banana_usda_nutrients(self) -> list[USDANutrient]:
        """Real USDA nutrient data for banana (per 100g).

        Source: USDA FoodData Central
        Food: Bananas, raw
        FDC ID: 173944
        """
        return [
            # Energy
            USDANutrient(
                number="208",
                name="Energy",
                amount=89.0,
                unit="kcal",
            ),
            # Macronutrients
            USDANutrient(
                number="203",
                name="Protein",
                amount=1.09,
                unit="g",
            ),
            USDANutrient(
                number="205",
                name="Carbohydrate, by difference",
                amount=22.84,
                unit="g",
            ),
            USDANutrient(
                number="204",
                name="Total lipid (fat)",
                amount=0.33,
                unit="g",
            ),
            # Fiber
            USDANutrient(
                number="291",
                name="Fiber, total dietary",
                amount=2.6,
                unit="g",
            ),
            # Sugars
            USDANutrient(
                number="269",
                name="Sugars, total including NLEA",
                amount=12.23,
                unit="g",
            ),
            # Sodium
            USDANutrient(
                number="307",
                name="Sodium, Na",
                amount=1.0,
                unit="mg",
            ),
        ]

    @pytest.fixture
    def banana_usda_food_item(self, banana_usda_nutrients: list[USDANutrient]) -> USDAFoodItem:
        """USDA food item for banana."""
        return USDAFoodItem(
            fdc_id="173944",
            description="Bananas, raw",
            data_type=USDADataType.SR_LEGACY,
            nutrients=banana_usda_nutrients,
        )

    @pytest.fixture
    def banana_usda_search_result(self, banana_usda_food_item: USDAFoodItem) -> USDASearchResult:
        """USDA search result for banana."""
        return USDASearchResult(
            total_hits=1,
            current_page=1,
            total_pages=1,
            foods=[banana_usda_food_item],
        )

    def test_banana_100g_nutrient_profile(self, banana_usda_food_item: USDAFoodItem) -> None:
        """Test mapping USDA banana data to nutrient profile (100g).

        Verifies:
        - Correct calorie calculation (89 kcal)
        - Proper macronutrient extraction
        - Micronutrient mapping (fiber, sugar, sodium)
        - USDA source attribution
        - High confidence score
        """
        # ACT - Map USDA data to domain profile
        profile = USDAMapper.to_nutrient_profile(banana_usda_food_item)

        # ASSERT - Verify 100g nutritional values
        assert isinstance(profile, NutrientProfile)

        # Energy
        assert profile.calories == 89

        # Macronutrients (exact USDA values, not rounded)
        assert profile.protein == 1.09
        assert profile.carbs == 22.84
        assert profile.fat == 0.33

        # Micronutrients
        assert profile.fiber == 2.6
        assert profile.sugar == 12.23  # Exact USDA value
        assert profile.sodium == 1.0

        # Metadata
        assert profile.source == NutrientSource.USDA
        assert profile.confidence >= 0.9  # High confidence for USDA
        assert profile.quantity_g == 100.0

    def test_banana_scaling_to_150g(self, banana_usda_food_item: USDAFoodItem) -> None:
        """Test scaling banana profile from 100g to 150g.

        Real-world scenario: User logs 1.5 bananas (150g)

        Expected values for 150g:
        - Calories: 89 * 1.5 = 133.5 → 133 kcal (int truncation)
        - Protein: 1.09 * 1.5 = 1.635 → 1.6g (rounded)
        - Carbs: 22.84 * 1.5 = 34.26 → 34.3g (rounded)
        - Fat: 0.33 * 1.5 = 0.495 → 0.5g (rounded)
        """
        # ARRANGE - Get base 100g profile
        profile_100g = USDAMapper.to_nutrient_profile(banana_usda_food_item)

        # ACT - Scale to 150g (1.5 bananas)
        profile_150g = profile_100g.scale_to_quantity(150.0)

        # ASSERT - Verify scaled values
        assert profile_150g.quantity_g == 150.0

        # Energy (int, truncated not rounded)
        assert profile_150g.calories == 133  # 89 * 1.5 = 133.5 → 133

        # Macronutrients (1 decimal, rounded)
        assert profile_150g.protein == 1.6  # 1.09 * 1.5 = 1.635 → 1.6
        assert profile_150g.carbs == 34.3  # 22.84 * 1.5 = 34.26 → 34.3
        assert profile_150g.fat == 0.5  # 0.33 * 1.5 = 0.495 → 0.5

        # Micronutrients
        assert profile_150g.fiber == 3.9  # 2.6 * 1.5 = 3.9
        assert profile_150g.sugar == 18.3  # 12.2 * 1.5 = 18.3
        assert profile_150g.sodium == 1.5  # 1.0 * 1.5 = 1.5

        # Metadata unchanged
        assert profile_150g.source == NutrientSource.USDA
        assert profile_150g.confidence == profile_100g.confidence

    def test_banana_scaling_to_medium_size(self, banana_usda_food_item: USDAFoodItem) -> None:
        """Test scaling to medium banana (118g).

        Real-world scenario: User logs 1 medium banana
        Average medium banana weight: 118g

        Expected values for 118g:
        - Calories: 89 * 1.18 = 105.02 → 105 kcal (int)
        - Protein: 1.09 * 1.18 = 1.2862 → 1.3g (rounded)
        - Carbs: 22.84 * 1.18 = 26.9512 → 27.0g (rounded)
        """
        # ARRANGE
        profile_100g = USDAMapper.to_nutrient_profile(banana_usda_food_item)

        # ACT - Scale to medium banana (118g)
        profile_medium = profile_100g.scale_to_quantity(118.0)

        # ASSERT
        assert profile_medium.quantity_g == 118.0
        assert profile_medium.calories == 105  # 89 * 1.18 = 105.02 → 105
        assert profile_medium.protein == 1.3  # 1.09 * 1.18 = 1.2862 → 1.3
        assert profile_medium.carbs == 27.0  # 22.84 * 1.18 = 26.9512 → 27.0
        assert profile_medium.fat == 0.4  # 0.33 * 1.18 = 0.3894 → 0.4

    def test_banana_search_result_extraction(
        self, banana_usda_search_result: USDASearchResult
    ) -> None:
        """Test extracting banana from search results.

        Verifies:
        - Search result structure
        - First result extraction
        - Pagination info
        """
        # ASSERT - Search result structure
        assert banana_usda_search_result.total_hits == 1
        assert banana_usda_search_result.current_page == 1
        assert len(banana_usda_search_result.foods) == 1

        # Extract first result
        banana = banana_usda_search_result.foods[0]
        assert banana.fdc_id == "173944"
        assert "banana" in banana.description.lower()
        assert banana.data_type == USDADataType.SR_LEGACY

    def test_banana_nutrient_completeness(self, banana_usda_food_item: USDAFoodItem) -> None:
        """Test that banana has all essential nutrients.

        Verifies all 7 key nutrients are present:
        - Energy (calories)
        - Protein
        - Carbohydrates
        - Fat
        - Fiber
        - Sugar
        - Sodium
        """
        # ARRANGE
        profile = USDAMapper.to_nutrient_profile(banana_usda_food_item)

        # ASSERT - All nutrients present
        assert profile.calories > 0
        assert profile.protein > 0
        assert profile.carbs > 0
        assert profile.fat >= 0  # Banana has very low fat
        assert profile.fiber is not None and profile.fiber > 0
        assert profile.sugar is not None and profile.sugar > 0
        assert profile.sodium is not None and profile.sodium >= 0

    def test_banana_to_dict_serialization(self, banana_usda_food_item: USDAFoodItem) -> None:
        """Test serialization to dict for storage.

        Verifies profile can be converted to dict for:
        - MongoDB storage
        - JSON API responses
        - Cache storage
        """
        # ARRANGE
        profile = USDAMapper.to_nutrient_profile(banana_usda_food_item)

        # ACT
        profile_dict = profile.to_dict()

        # ASSERT
        assert isinstance(profile_dict, dict)
        assert profile_dict["calories"] == 89
        assert profile_dict["protein"] == 1.09  # Exact USDA value
        assert profile_dict["source"] == "USDA"  # Enum converted to value
        assert "confidence" in profile_dict
        assert "quantity_g" in profile_dict

    def test_banana_macros_ratio(self, banana_usda_food_item: USDAFoodItem) -> None:
        """Test banana macronutrient ratio (carb-heavy).

        Banana is known for high carbs, low protein/fat.
        Typical ratio: ~90% carbs, ~5% protein, ~3% fat
        """
        # ARRANGE
        profile = USDAMapper.to_nutrient_profile(banana_usda_food_item)

        # Calculate macro percentages
        total_macros = profile.protein + profile.carbs + profile.fat

        carb_pct = (profile.carbs / total_macros) * 100
        protein_pct = (profile.protein / total_macros) * 100
        fat_pct = (profile.fat / total_macros) * 100

        # ASSERT - Banana is carb-dominant
        assert carb_pct > 85  # Should be ~94%
        assert protein_pct < 10  # Should be ~4%
        assert fat_pct < 5  # Should be ~1%

    def test_banana_zero_quantity_error(self, banana_usda_food_item: USDAFoodItem) -> None:
        """Test that scaling to 0g raises error."""
        # ARRANGE
        profile = USDAMapper.to_nutrient_profile(banana_usda_food_item)

        # ACT & ASSERT - Should raise ValueError
        with pytest.raises(ValueError, match="must be positive"):
            profile.scale_to_quantity(0.0)

    def test_banana_negative_quantity_error(self, banana_usda_food_item: USDAFoodItem) -> None:
        """Test that scaling to negative quantity raises error."""
        # ARRANGE
        profile = USDAMapper.to_nutrient_profile(banana_usda_food_item)

        # ACT & ASSERT - Should raise ValueError
        with pytest.raises(ValueError, match="must be positive"):
            profile.scale_to_quantity(-50.0)
