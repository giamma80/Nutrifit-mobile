"""Unit tests for MacroService."""

from domain.nutritional_profile.calculation.macro_service import MacroService
from domain.nutritional_profile.core.value_objects import Goal


class TestMacroService:
    """Test macro calculation with goal-specific distributions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = MacroService()

    def test_calculate_macros_cut_goal(self):
        """Test macro calculation for cut goal."""
        calories = 2000.0
        weight = 80.0
        goal = Goal.CUT

        macros = self.service.calculate(calories, weight, goal)

        # Protein: 2.2 g/kg = 176g = 704 kcal
        assert macros.protein_g == 176.0
        # Fat: 25% = 500 kcal = ~56g (rounded from 55.56)
        assert abs(macros.fat_g - 56) <= 1
        # Carbs: remainder = 796 kcal = 199g
        assert macros.carbs_g == 199

    def test_calculate_macros_maintain_goal(self):
        """Test macro calculation for maintain goal."""
        calories = 2500.0
        weight = 75.0
        goal = Goal.MAINTAIN

        macros = self.service.calculate(calories, weight, goal)

        # Protein: 1.8 g/kg = 135g = 540 kcal
        assert macros.protein_g == 135.0
        # Fat: 30% = 750 kcal = ~83g (rounded from 83.33)
        assert abs(macros.fat_g - 83) <= 1
        # Carbs: remainder = 1210 kcal = 302g
        assert macros.carbs_g == 302

    def test_calculate_macros_bulk_goal(self):
        """Test macro calculation for bulk goal."""
        calories = 3000.0
        weight = 90.0
        goal = Goal.BULK

        macros = self.service.calculate(calories, weight, goal)

        # Protein: 2.0 g/kg = 180g = 720 kcal
        assert macros.protein_g == 180.0
        # Fat: 20% = 600 kcal = ~67g (rounded from 66.67)
        assert abs(macros.fat_g - 67) <= 1
        # Carbs: remainder = 1680 kcal = 420g
        assert macros.carbs_g == 420

    def test_calculate_macros_total_calories_matches_target(self):
        """Test that total calories from macros matches target."""
        calories = 2200.0
        weight = 70.0

        for goal in Goal:
            macros = self.service.calculate(calories, weight, goal)
            total = macros.total_calories()

            # Allow 1% tolerance for rounding
            assert abs(total - calories) / calories < 0.01

    def test_calculate_macros_different_weights_affect_protein(self):
        """Test that weight affects protein calculation."""
        calories = 2000.0
        goal = Goal.CUT

        macros_60kg = self.service.calculate(calories, 60.0, goal)
        macros_100kg = self.service.calculate(calories, 100.0, goal)

        # Higher weight = more protein (2.2 g/kg for cut)
        assert macros_100kg.protein_g > macros_60kg.protein_g
        assert macros_100kg.protein_g == 220.0  # 100 * 2.2
        assert macros_60kg.protein_g == 132.0  # 60 * 2.2

    def test_calculate_macros_protein_multiplier_by_goal(self):
        """Test protein multiplier varies by goal."""
        calories = 2500.0
        weight = 80.0

        macros_cut = self.service.calculate(calories, weight, Goal.CUT)
        macros_maintain = self.service.calculate(calories, weight, Goal.MAINTAIN)
        macros_bulk = self.service.calculate(calories, weight, Goal.BULK)

        # Cut: 2.2 g/kg = 176g
        assert macros_cut.protein_g == 176.0
        # Maintain: 1.8 g/kg = 144g
        assert macros_maintain.protein_g == 144.0
        # Bulk: 2.0 g/kg = 160g
        assert macros_bulk.protein_g == 160.0

    def test_calculate_macros_fat_percentage_by_goal(self):
        """Test fat percentage varies by goal."""
        calories = 2000.0
        weight = 80.0

        macros_cut = self.service.calculate(calories, weight, Goal.CUT)
        macros_maintain = self.service.calculate(calories, weight, Goal.MAINTAIN)
        macros_bulk = self.service.calculate(calories, weight, Goal.BULK)

        # Cut: 25% fat
        assert abs(macros_cut.fat_percentage() - 25.0) < 1.0
        # Maintain: 30% fat
        assert abs(macros_maintain.fat_percentage() - 30.0) < 1.0
        # Bulk: 20% fat
        assert abs(macros_bulk.fat_percentage() - 20.0) < 1.0

    def test_calculate_macros_carbs_is_remainder(self):
        """Test that carbs fill remaining calories."""
        calories = 2400.0
        weight = 75.0
        goal = Goal.MAINTAIN

        macros = self.service.calculate(calories, weight, goal)

        # Protein: 1.8*75 = 135g = 540 kcal
        protein_cals = 135 * 4
        # Fat: 30% = 720 kcal
        fat_cals = 2400 * 0.30
        # Carbs: remainder = 1140 kcal = 285g
        expected_carbs_cals = 2400 - protein_cals - fat_cals

        actual_carbs_cals = macros.carbs_g * 4
        assert abs(actual_carbs_cals - expected_carbs_cals) < 1.0

    def test_calculate_macros_returns_macro_split_object(self):
        """Test that calculate returns MacroSplit value object."""
        calories = 2000.0
        weight = 70.0
        goal = Goal.CUT

        result = self.service.calculate(calories, weight, goal)

        assert hasattr(result, "protein_g")
        assert hasattr(result, "carbs_g")
        assert hasattr(result, "fat_g")
        assert hasattr(result, "total_calories")

    def test_calculate_macros_low_calorie_target(self):
        """Test macro calculation with low calorie target."""
        calories = 1500.0
        weight = 60.0
        goal = Goal.CUT

        macros = self.service.calculate(calories, weight, goal)

        # Should still calculate valid macros
        assert macros.protein_g == 132.0  # 60 * 2.2
        assert macros.fat_g > 0
        assert macros.carbs_g > 0
        assert abs(macros.total_calories() - 1500) / 1500 < 0.01

    def test_calculate_macros_high_calorie_target(self):
        """Test macro calculation with high calorie target."""
        calories = 4000.0
        weight = 100.0
        goal = Goal.BULK

        macros = self.service.calculate(calories, weight, goal)

        # Should still calculate valid macros
        assert macros.protein_g == 200.0  # 100 * 2.0
        assert macros.fat_g > 0
        assert macros.carbs_g > 0
        assert abs(macros.total_calories() - 4000) / 4000 < 0.01

    def test_calculate_macros_percentages_sum_to_100(self):
        """Test that macro percentages sum to approximately 100%."""
        calories = 2200.0
        weight = 75.0

        for goal in Goal:
            macros = self.service.calculate(calories, weight, goal)

            total_percent = (
                macros.protein_percentage() + macros.carbs_percentage() + macros.fat_percentage()
            )

            # Allow small rounding error
            assert abs(total_percent - 100.0) < 0.1
