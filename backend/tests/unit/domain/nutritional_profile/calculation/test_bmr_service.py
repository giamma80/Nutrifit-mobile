"""Unit tests for BMRService."""

from domain.nutritional_profile.calculation.bmr_service import BMRService
from domain.nutritional_profile.core.value_objects import (
    ActivityLevel,
    UserData,
)


class TestBMRService:
    """Test BMR calculation using Mifflin-St Jeor formula."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = BMRService()

    def test_calculate_bmr_male(self):
        """Test BMR calculation for male."""
        # Test case from documentation
        user_data = UserData(
            weight=80.0, height=180.0, age=30, sex="M", activity_level=ActivityLevel.MODERATE
        )

        bmr = self.service.calculate(user_data)

        # Expected: 10*80 + 6.25*180 - 5*30 + 5 = 1780
        assert bmr.value == 1780.0

    def test_calculate_bmr_female(self):
        """Test BMR calculation for female."""
        user_data = UserData(
            weight=60.0, height=165.0, age=25, sex="F", activity_level=ActivityLevel.LIGHT
        )

        bmr = self.service.calculate(user_data)

        # Expected: 10*60 + 6.25*165 - 5*25 - 161 = 1345.25
        assert bmr.value == 1345.25

    def test_calculate_bmr_different_ages(self):
        """Test that age affects BMR calculation."""
        base_data = UserData(
            weight=70.0, height=170.0, age=25, sex="M", activity_level=ActivityLevel.MODERATE
        )

        older_data = UserData(
            weight=70.0, height=170.0, age=50, sex="M", activity_level=ActivityLevel.MODERATE
        )

        bmr_young = self.service.calculate(base_data)
        bmr_old = self.service.calculate(older_data)

        # Older age should have lower BMR (5 kcal/year difference)
        assert bmr_young.value > bmr_old.value
        assert bmr_young.value - bmr_old.value == 125.0  # 25 years * 5

    def test_calculate_bmr_different_weights(self):
        """Test that weight affects BMR calculation."""
        lighter = UserData(
            weight=60.0, height=170.0, age=30, sex="M", activity_level=ActivityLevel.MODERATE
        )

        heavier = UserData(
            weight=80.0, height=170.0, age=30, sex="M", activity_level=ActivityLevel.MODERATE
        )

        bmr_lighter = self.service.calculate(lighter)
        bmr_heavier = self.service.calculate(heavier)

        # Heavier should have higher BMR (10 kcal/kg difference)
        assert bmr_heavier.value > bmr_lighter.value
        assert bmr_heavier.value - bmr_lighter.value == 200.0  # 20kg * 10

    def test_calculate_bmr_different_heights(self):
        """Test that height affects BMR calculation."""
        shorter = UserData(
            weight=70.0, height=160.0, age=30, sex="M", activity_level=ActivityLevel.MODERATE
        )

        taller = UserData(
            weight=70.0, height=180.0, age=30, sex="M", activity_level=ActivityLevel.MODERATE
        )

        bmr_shorter = self.service.calculate(shorter)
        bmr_taller = self.service.calculate(taller)

        # Taller should have higher BMR (6.25 kcal/cm difference)
        assert bmr_taller.value > bmr_shorter.value
        assert bmr_taller.value - bmr_shorter.value == 125.0  # 20cm * 6.25

    def test_calculate_bmr_sex_difference(self):
        """Test that sex affects BMR calculation."""
        male = UserData(
            weight=70.0, height=170.0, age=30, sex="M", activity_level=ActivityLevel.MODERATE
        )

        female = UserData(
            weight=70.0, height=170.0, age=30, sex="F", activity_level=ActivityLevel.MODERATE
        )

        bmr_male = self.service.calculate(male)
        bmr_female = self.service.calculate(female)

        # Male should have higher BMR (166 kcal difference: +5 vs -161)
        assert bmr_male.value > bmr_female.value
        assert bmr_male.value - bmr_female.value == 166.0

    def test_calculate_bmr_returns_bmr_object(self):
        """Test that calculate returns BMR value object."""
        user_data = UserData(
            weight=70.0, height=170.0, age=30, sex="M", activity_level=ActivityLevel.MODERATE
        )

        result = self.service.calculate(user_data)

        assert hasattr(result, "value")
        assert isinstance(result.value, float)
        assert result.value > 0

    def test_calculate_bmr_activity_level_not_used(self):
        """Test that activity level doesn't affect BMR (only TDEE)."""
        sedentary = UserData(
            weight=70.0, height=170.0, age=30, sex="M", activity_level=ActivityLevel.SEDENTARY
        )

        very_active = UserData(
            weight=70.0, height=170.0, age=30, sex="M", activity_level=ActivityLevel.VERY_ACTIVE
        )

        bmr_sedentary = self.service.calculate(sedentary)
        bmr_active = self.service.calculate(very_active)

        # BMR should be same regardless of activity
        assert bmr_sedentary.value == bmr_active.value
