"""Unit tests for TDEEService."""

from domain.nutritional_profile.calculation.tdee_service import TDEEService
from domain.nutritional_profile.core.value_objects import (
    ActivityLevel,
    BMR,
)


class TestTDEEService:
    """Test TDEE calculation using PAL multipliers."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = TDEEService()
        self.base_bmr = BMR(1800.0)

    def test_calculate_tdee_sedentary(self):
        """Test TDEE for sedentary activity level."""
        activity = ActivityLevel.SEDENTARY

        tdee = self.service.calculate(self.base_bmr, activity)

        # Expected: 1800 * 1.2 = 2160
        assert tdee.value == 2160.0

    def test_calculate_tdee_light(self):
        """Test TDEE for light activity level."""
        activity = ActivityLevel.LIGHT

        tdee = self.service.calculate(self.base_bmr, activity)

        # Expected: 1800 * 1.375 = 2475
        assert tdee.value == 2475.0

    def test_calculate_tdee_moderate(self):
        """Test TDEE for moderate activity level."""
        activity = ActivityLevel.MODERATE

        tdee = self.service.calculate(self.base_bmr, activity)

        # Expected: 1800 * 1.55 = 2790
        assert tdee.value == 2790.0

    def test_calculate_tdee_active(self):
        """Test TDEE for active activity level."""
        activity = ActivityLevel.ACTIVE

        tdee = self.service.calculate(self.base_bmr, activity)

        # Expected: 1800 * 1.725 = 3105
        assert tdee.value == 3105.0

    def test_calculate_tdee_very_active(self):
        """Test TDEE for very active level."""
        activity = ActivityLevel.VERY_ACTIVE

        tdee = self.service.calculate(self.base_bmr, activity)

        # Expected: 1800 * 1.9 = 3420
        assert tdee.value == 3420.0

    def test_calculate_tdee_all_levels_progressive(self):
        """Test that TDEE increases progressively with activity."""
        levels = [
            ActivityLevel.SEDENTARY,
            ActivityLevel.LIGHT,
            ActivityLevel.MODERATE,
            ActivityLevel.ACTIVE,
            ActivityLevel.VERY_ACTIVE,
        ]

        tdees = [self.service.calculate(self.base_bmr, level) for level in levels]

        # Each level should be higher than previous
        for i in range(len(tdees) - 1):
            assert tdees[i].value < tdees[i + 1].value

    def test_calculate_tdee_with_different_bmr_values(self):
        """Test TDEE scales correctly with different BMR values."""
        low_bmr = BMR(1500.0)
        high_bmr = BMR(2500.0)
        activity = ActivityLevel.MODERATE

        tdee_low = self.service.calculate(low_bmr, activity)
        tdee_high = self.service.calculate(high_bmr, activity)

        # TDEE should scale proportionally
        # 1500 * 1.55 = 2325
        assert tdee_low.value == 2325.0
        # 2500 * 1.55 = 3875
        assert tdee_high.value == 3875.0

    def test_calculate_tdee_returns_tdee_object(self):
        """Test that calculate returns TDEE value object."""
        activity = ActivityLevel.MODERATE

        result = self.service.calculate(self.base_bmr, activity)

        assert hasattr(result, "value")
        assert isinstance(result.value, float)
        assert result.value > 0

    def test_calculate_tdee_always_greater_than_bmr(self):
        """Test that TDEE is always greater than BMR."""
        bmr = BMR(1600.0)

        for activity in ActivityLevel:
            tdee = self.service.calculate(bmr, activity)
            assert tdee.value > bmr.value

    def test_calculate_tdee_pal_multipliers_match_spec(self):
        """Test that PAL multipliers match documentation."""
        base_bmr = BMR(1000.0)  # Use round number for easy verification

        expected = {
            ActivityLevel.SEDENTARY: 1200.0,  # 1.2
            ActivityLevel.LIGHT: 1375.0,  # 1.375
            ActivityLevel.MODERATE: 1550.0,  # 1.55
            ActivityLevel.ACTIVE: 1725.0,  # 1.725
            ActivityLevel.VERY_ACTIVE: 1900.0,  # 1.9
        }

        for activity, expected_tdee in expected.items():
            tdee = self.service.calculate(base_bmr, activity)
            assert tdee.value == expected_tdee
