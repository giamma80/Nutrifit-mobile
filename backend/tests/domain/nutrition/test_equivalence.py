"""Test equivalence nutrition domain vs existing logic.

Verifica che i calcoli del nuovo dominio nutrition/ producano
risultati identici alla logica esistente in rules/category_profiles.py
e app.py daily_summary.
"""

import pytest
from typing import Any
from unittest.mock import Mock

from domain.nutrition.application.nutrition_service import (
    NutritionCalculationService,
)
from domain.nutrition.model import (
    UserPhysicalData,
    ActivityLevel,
    GoalStrategy,
    NutrientValues,
)
from domain.nutrition.adapters.category_adapter import CategoryProfileAdapter
from rules.category_profiles import (
    recompute_calories as legacy_recompute_calories,
    NormalizedItem as LegacyNormalizedItem,
    garnish_clamp as legacy_garnish_clamp,
)


class TestNutritionCalculationEquivalence:
    """Test equivalenza calcoli BMR/TDEE/macro targets."""

    @pytest.fixture(autouse=True)
    def setup_nutrition_service(self, enable_nutrition_domain_v2: Any) -> None:
        """Setup service con feature flag abilitato automaticamente."""
        # Mock ports for isolated testing
        self.nutrition_plan_port = Mock()
        self.meal_data_port = Mock()
        self.activity_data_port = Mock()
        self.category_profile_port = CategoryProfileAdapter()

        self.service = NutritionCalculationService(
            nutrition_plan_port=self.nutrition_plan_port,
            meal_data_port=self.meal_data_port,
            activity_data_port=self.activity_data_port,
            category_profile_port=self.category_profile_port,
        )

    def test_bmr_calculation_mifflin_st_jeor(self) -> None:
        """Test formula BMR Mifflin-St Jeor equivalente per maschi/femmine."""

        # Male example
        male_data = UserPhysicalData(
            age=30,
            weight_kg=75.0,
            height_cm=180.0,
            sex="male",
            activity_level=ActivityLevel.MODERATELY_ACTIVE,
        )

        bmr_male = self.service.calculate_bmr(male_data)
        expected_male = 10 * 75 + 6.25 * 180 - 5 * 30 + 5  # 1675
        assert abs(bmr_male - expected_male) < 0.1

        # Female example
        female_data = UserPhysicalData(
            age=25,
            weight_kg=60.0,
            height_cm=165.0,
            sex="female",
            activity_level=ActivityLevel.LIGHTLY_ACTIVE,
        )

        bmr_female = self.service.calculate_bmr(female_data)
        expected_female = 10 * 60 + 6.25 * 165 - 5 * 25 - 161  # 1346.25
        assert abs(bmr_female - expected_female) < 0.1

    def test_tdee_calculation_activity_multipliers(self) -> None:
        """Test calcolo TDEE con moltiplicatori attività."""

        base_bmr = 1500.0

        test_cases = [
            (ActivityLevel.SEDENTARY, 1500 * 1.2),
            (ActivityLevel.LIGHTLY_ACTIVE, 1500 * 1.375),
            (ActivityLevel.MODERATELY_ACTIVE, 1500 * 1.55),
            (ActivityLevel.VERY_ACTIVE, 1500 * 1.725),
            (ActivityLevel.EXTREMELY_ACTIVE, 1500 * 1.9),
        ]

        for activity_level, expected_tdee in test_cases:
            tdee = self.service.calculate_tdee(base_bmr, activity_level)
            assert abs(tdee - expected_tdee) < 0.1

    def test_macro_targets_calorie_distribution(self) -> None:
        """Test distribuzione calorica macro: 4kcal/g protein+carbs, 9kcal/g fat."""

        tdee = 2000.0
        physical_data = UserPhysicalData(
            age=30,
            weight_kg=70.0,
            height_cm=175.0,
            sex="male",
            activity_level=ActivityLevel.MODERATELY_ACTIVE,
        )

        # Test CUT strategy (-20%)
        targets_cut = self.service.calculate_macro_targets(
            tdee=tdee,
            strategy=GoalStrategy.CUT,
            physical_data=physical_data,
        )

        expected_calories = int(2000 * 0.8)  # 1600
        assert targets_cut.calories == expected_calories

        # Verify calorie distribution (protein: 4kcal/g, fat: 9kcal/g, carbs: 4kcal/g)
        protein_kcal = targets_cut.protein_g * 4
        fat_kcal = targets_cut.fat_g * 9
        carbs_kcal = targets_cut.carbs_g * 4
        total_macro_kcal = protein_kcal + fat_kcal + carbs_kcal

        # Should be very close to target calories
        assert abs(total_macro_kcal - expected_calories) < 50

        # Protein should be ~1.8g/kg
        expected_protein = 70 * 1.8  # 126g
        assert abs(targets_cut.protein_g - expected_protein) < 10

    def test_recompute_calories_equivalence(self) -> None:
        """Test equivalenza recompute_calories vs legacy."""

        test_cases = [
            # (protein, carbs, fat, existing_calories, should_correct)
            (20.0, 30.0, 10.0, None, True),  # Missing calories
            (20.0, 30.0, 10.0, 290.0, False),  # Consistent calories
            (20.0, 30.0, 10.0, 200.0, True),  # Inconsistent calories
        ]

        for protein, carbs, fat, existing_calories, should_correct in test_cases:
            # New domain calculation
            nutrients = NutrientValues(
                protein=protein,
                carbs=carbs,
                fat=fat,
                calories=existing_calories,
            )

            new_calories, was_corrected = self.service.recompute_calories_from_macros(nutrients)

            # Legacy calculation
            legacy_item = LegacyNormalizedItem(
                label="test",
                quantity_g=100.0,
                calories=existing_calories,
                protein=protein,
                carbs=carbs,
                fat=fat,
                fiber=2.0,
                sugar=1.0,
                sodium=0.05,
            )

            legacy_calories, legacy_corrected = legacy_recompute_calories(legacy_item)

            # Should match
            assert was_corrected == legacy_corrected
            if new_calories is not None and legacy_calories is not None:
                assert abs(new_calories - legacy_calories) < 0.1


class TestCategoryProfileEquivalence:
    """Test equivalenza classificazione categorie e garnish clamp."""

    def setup_method(self) -> None:
        self.adapter = CategoryProfileAdapter()

    def test_category_classification_equivalence(self) -> None:
        """Test classificazione categoria equivalente a legacy logic."""

        # Test core mappings that should work
        core_cases = [
            ("salmone alla griglia", "lean_fish"),
            ("petto di pollo", "poultry"),
            ("pasta al pomodoro", "pasta_cooked"),
            ("riso basmati", "rice_cooked"),
            ("fagioli cannellini", "legume"),
            ("insalata mista", "leafy_salad"),
            ("latte intero", "dairy_basic"),
            ("limone spremuto", "citrus_garnish"),
            ("basilico fresco", "herb"),
        ]

        for food_label, expected_category in core_cases:
            result = self.adapter.classify_food(food_label)
            assert (
                result == expected_category
            ), f"Failed: {food_label} -> {result} (expected {expected_category})"

        # Test pattern variations
        assert self.adapter.classify_food("patate") == "tuber"
        assert self.adapter.classify_food("patata fritta") == "tuber"
        assert self.adapter.classify_food("potato") == "tuber"

    def test_garnish_clamp_equivalence(self) -> None:
        """Test garnish clamp equivalente tra nuovo e legacy."""

        test_cases = [
            # (quantity, category, expected_quantity, expected_clamped)
            (3.0, "citrus_garnish", 5.0, True),  # Below min
            (7.0, "citrus_garnish", 7.0, False),  # Within range
            (15.0, "citrus_garnish", 10.0, True),  # Above max
            (3.0, "poultry", 3.0, False),  # Non-garnish
            (15.0, "herb", 10.0, True),  # Herb garnish clamp
        ]

        for quantity, category, expected_qty, expected_clamped in test_cases:
            # New domain
            new_qty, new_clamped = self.adapter.apply_garnish_clamp(quantity, category)

            # Legacy
            legacy_qty, legacy_clamped = legacy_garnish_clamp(quantity, category)

            assert abs(new_qty - legacy_qty) < 0.1
            assert new_clamped == legacy_clamped
            assert abs(new_qty - expected_qty) < 0.1
            assert new_clamped == expected_clamped

    def test_category_profiles_data_equivalence(self) -> None:
        """Test che i dati dei profili siano equivalenti al legacy."""

        from rules.category_profiles import CATEGORY_PROFILES as LEGACY_PROFILES

        for category_name in LEGACY_PROFILES.keys():
            profile = self.adapter.get_profile(category_name)
            assert profile is not None, f"Missing profile: {category_name}"

            legacy_data = LEGACY_PROFILES[category_name]

            # Check nutrients match per 100g
            nutrients = profile.nutrients_per_100g
            assert nutrients.protein is not None
            assert nutrients.carbs is not None
            assert nutrients.fat is not None
            assert nutrients.fiber is not None
            assert nutrients.sugar is not None
            assert nutrients.sodium is not None
            assert abs(nutrients.protein - legacy_data["protein"]) < 0.1
            assert abs(nutrients.carbs - legacy_data["carbs"]) < 0.1
            assert abs(nutrients.fat - legacy_data["fat"]) < 0.1
            assert abs(nutrients.fiber - legacy_data["fiber"]) < 0.1
            assert abs(nutrients.sugar - legacy_data["sugar"]) < 0.1
            assert abs(nutrients.sodium - legacy_data["sodium"]) < 0.1


@pytest.mark.integration
@pytest.mark.skip("Mock integration tests need rework")
class TestDailySummaryEquivalence:
    """Integration test daily summary calculation vs app.py logic."""

    def setup_method(self) -> None:
        self.meal_data_port = Mock()
        self.activity_data_port = Mock()
        self.nutrition_plan_port = Mock()
        self.category_profile_port = Mock()

        self.service = NutritionCalculationService(
            nutrition_plan_port=self.nutrition_plan_port,
            meal_data_port=self.meal_data_port,
            activity_data_port=self.activity_data_port,
            category_profile_port=self.category_profile_port,
        )

    def test_daily_summary_deficit_calculation(self) -> None:
        """Test calcolo deficit calorico nel summary."""

        # Mock data
        self.meal_data_port.get_daily_meals.return_value = [
            {"calories": 300},
            {"calories": 450},
            {"calories": 350},
        ]
        self.meal_data_port.get_daily_totals.return_value = NutrientValues(
            calories=1100,
            protein=80.0,
            carbs=120.0,
            fat=40.0,
        )
        self.activity_data_port.get_daily_activity.return_value = {
            "steps": 8500,
            "calories_out": 1800.0,
        }

        summary = self.service.calculate_daily_summary(
            user_id="test_user",
            date="2024-01-15",
        )

        # Expected calculations (matching app.py logic)
        expected_deficit = int(round(1800 - 1100))  # 700
        expected_replenished_pct = int(round((1100 / 1800) * 100))  # 61

        assert summary.calories_deficit == expected_deficit
        assert summary.calories_replenished_percent == expected_replenished_pct
        assert summary.meal_count == 3
        assert summary.activity_steps == 8500
        assert summary.activity_calories_out == 1800.0

    def test_daily_summary_edge_cases(self) -> None:
        """Test edge cases nel daily summary."""

        # Zero calories out case
        self.meal_data_port.get_daily_totals.return_value = NutrientValues(calories=500)
        self.activity_data_port.get_daily_activity.return_value = {
            "steps": 0,
            "calories_out": 0.0,
        }

        summary = self.service.calculate_daily_summary("user", "2024-01-15")
        assert summary.calories_replenished_percent == 0

        # Surplus case (ate more than burned)
        self.activity_data_port.get_daily_activity.return_value = {
            "steps": 5000,
            "calories_out": 1500.0,
        }
        self.meal_data_port.get_daily_totals.return_value = NutrientValues(calories=2000)

        summary = self.service.calculate_daily_summary("user", "2024-01-15")
        assert summary.calories_deficit == -500  # Negative = surplus
        expected_pct = int(round((2000 / 1500) * 100))  # 133%
        assert summary.calories_replenished_percent == expected_pct
