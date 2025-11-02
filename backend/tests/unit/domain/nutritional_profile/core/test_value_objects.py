"""Unit tests for nutritional profile value objects."""

import uuid

import pytest

from domain.nutritional_profile.core.value_objects import (
    ActivityLevel,
    BMR,
    Goal,
    MacroSplit,
    ProfileId,
    TDEE,
    UserData,
)
from domain.nutritional_profile.core.exceptions.domain_errors import (
    InvalidUserDataError,
)


class TestProfileId:
    """Test ProfileId value object."""

    def test_generate_creates_valid_uuid(self):
        """Test that generate creates a valid UUID."""
        profile_id = ProfileId.generate()

        assert isinstance(profile_id.value, uuid.UUID)
        assert profile_id.value.version == 4

    def test_from_string_valid_uuid(self):
        """Test creating ProfileId from valid UUID string."""
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        profile_id = ProfileId.from_string(uuid_str)

        assert str(profile_id.value) == uuid_str

    def test_from_string_invalid_uuid_raises(self):
        """Test that invalid UUID string raises ValueError."""
        with pytest.raises(ValueError, match="Invalid profile ID format"):
            ProfileId.from_string("not-a-uuid")

    def test_equality(self):
        """Test ProfileId equality."""
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        id1 = ProfileId.from_string(uuid_str)
        id2 = ProfileId.from_string(uuid_str)

        assert id1 == id2

    def test_different_ids_not_equal(self):
        """Test different ProfileIds are not equal."""
        id1 = ProfileId.generate()
        id2 = ProfileId.generate()

        assert id1 != id2


class TestGoal:
    """Test Goal enum."""

    def test_calorie_adjustment_cut(self):
        """Test calorie adjustment for cut goal."""
        tdee = 2500.0
        target = Goal.CUT.calorie_adjustment(tdee)

        assert target == 2000.0  # -500

    def test_calorie_adjustment_maintain(self):
        """Test calorie adjustment for maintain goal."""
        tdee = 2500.0
        target = Goal.MAINTAIN.calorie_adjustment(tdee)

        assert target == 2500.0  # no change

    def test_calorie_adjustment_bulk(self):
        """Test calorie adjustment for bulk goal."""
        tdee = 2500.0
        target = Goal.BULK.calorie_adjustment(tdee)

        assert target == 2800.0  # +300

    def test_protein_multiplier_cut(self):
        """Test protein multiplier for cut goal."""
        assert Goal.CUT.protein_multiplier() == 2.2

    def test_protein_multiplier_maintain(self):
        """Test protein multiplier for maintain goal."""
        assert Goal.MAINTAIN.protein_multiplier() == 1.8

    def test_protein_multiplier_bulk(self):
        """Test protein multiplier for bulk goal."""
        assert Goal.BULK.protein_multiplier() == 2.0

    def test_fat_percentage_cut(self):
        """Test fat percentage for cut goal."""
        assert Goal.CUT.fat_percentage() == 0.25

    def test_fat_percentage_maintain(self):
        """Test fat percentage for maintain goal."""
        assert Goal.MAINTAIN.fat_percentage() == 0.30

    def test_fat_percentage_bulk(self):
        """Test fat percentage for bulk goal."""
        assert Goal.BULK.fat_percentage() == 0.20


class TestActivityLevel:
    """Test ActivityLevel enum."""

    def test_pal_multiplier_sedentary(self):
        """Test PAL multiplier for sedentary."""
        assert ActivityLevel.SEDENTARY.pal_multiplier() == 1.2

    def test_pal_multiplier_light(self):
        """Test PAL multiplier for light activity."""
        assert ActivityLevel.LIGHT.pal_multiplier() == 1.375

    def test_pal_multiplier_moderate(self):
        """Test PAL multiplier for moderate activity."""
        assert ActivityLevel.MODERATE.pal_multiplier() == 1.55

    def test_pal_multiplier_active(self):
        """Test PAL multiplier for active."""
        assert ActivityLevel.ACTIVE.pal_multiplier() == 1.725

    def test_pal_multiplier_very_active(self):
        """Test PAL multiplier for very active."""
        assert ActivityLevel.VERY_ACTIVE.pal_multiplier() == 1.9


class TestUserData:
    """Test UserData value object."""

    def test_create_valid_user_data(self):
        """Test creating valid UserData."""
        data = UserData(
            weight=70.0, height=175.0, age=30, sex="M", activity_level=ActivityLevel.MODERATE
        )

        assert data.weight == 70.0
        assert data.height == 175.0
        assert data.age == 30
        assert data.sex == "M"
        assert data.activity_level == ActivityLevel.MODERATE

    def test_weight_must_be_positive(self):
        """Test that weight must be in valid range."""
        with pytest.raises(InvalidUserDataError, match="Weight must be"):
            UserData(
                weight=0.0, height=175.0, age=30, sex="M", activity_level=ActivityLevel.MODERATE
            )

    def test_height_must_be_positive(self):
        """Test that height must be in valid range."""
        with pytest.raises(InvalidUserDataError, match="Height must be"):
            UserData(
                weight=70.0, height=-175.0, age=30, sex="M", activity_level=ActivityLevel.MODERATE
            )

    def test_age_must_be_positive(self):
        """Test that age must be in valid range."""
        with pytest.raises(InvalidUserDataError, match="Age must be"):
            UserData(
                weight=70.0, height=175.0, age=0, sex="M", activity_level=ActivityLevel.MODERATE
            )

    def test_sex_must_be_valid(self):
        """Test that sex must be M or F."""
        with pytest.raises(InvalidUserDataError, match="Sex must be"):
            UserData(
                weight=70.0,
                height=175.0,
                age=30,
                sex="X",  # type: ignore
                activity_level=ActivityLevel.MODERATE,
            )

    def test_bmi_calculation(self):
        """Test BMI calculation."""
        data = UserData(
            weight=80.0, height=180.0, age=30, sex="M", activity_level=ActivityLevel.MODERATE
        )

        # BMI = 80 / (1.8^2) = 24.69
        assert abs(data.bmi() - 24.69) < 0.01

    def test_bmi_category_underweight(self):
        """Test BMI category for underweight."""
        data = UserData(
            weight=50.0, height=180.0, age=30, sex="M", activity_level=ActivityLevel.MODERATE
        )

        assert data.bmi_category() == "underweight"

    def test_bmi_category_normal(self):
        """Test BMI category for normal weight."""
        data = UserData(
            weight=70.0, height=175.0, age=30, sex="M", activity_level=ActivityLevel.MODERATE
        )

        assert data.bmi_category() == "normal"

    def test_bmi_category_overweight(self):
        """Test BMI category for overweight."""
        data = UserData(
            weight=85.0, height=175.0, age=30, sex="M", activity_level=ActivityLevel.MODERATE
        )

        assert data.bmi_category() == "overweight"

    def test_bmi_category_obese(self):
        """Test BMI category for obese."""
        data = UserData(
            weight=100.0, height=175.0, age=30, sex="M", activity_level=ActivityLevel.MODERATE
        )

        assert data.bmi_category() == "obese"


class TestBMR:
    """Test BMR value object."""

    def test_create_valid_bmr(self):
        """Test creating valid BMR."""
        bmr = BMR(1800.0)
        assert bmr.value == 1800.0

    def test_bmr_must_be_positive(self):
        """Test that BMR must be positive."""
        with pytest.raises(ValueError, match="BMR must be positive"):
            BMR(0.0)

    def test_bmr_negative_raises(self):
        """Test that negative BMR raises ValueError."""
        with pytest.raises(ValueError, match="BMR must be positive"):
            BMR(-100.0)


class TestTDEE:
    """Test TDEE value object."""

    def test_create_valid_tdee(self):
        """Test creating valid TDEE."""
        tdee = TDEE(2500.0)
        assert tdee.value == 2500.0

    def test_tdee_must_be_positive(self):
        """Test that TDEE must be positive."""
        with pytest.raises(ValueError, match="TDEE must be positive"):
            TDEE(0.0)

    def test_tdee_negative_raises(self):
        """Test that negative TDEE raises ValueError."""
        with pytest.raises(ValueError, match="TDEE must be positive"):
            TDEE(-100.0)


class TestMacroSplit:
    """Test MacroSplit value object."""

    def test_create_valid_macro_split(self):
        """Test creating valid MacroSplit."""
        macros = MacroSplit(protein_g=150, carbs_g=250, fat_g=70)

        assert macros.protein_g == 150
        assert macros.carbs_g == 250
        assert macros.fat_g == 70

    def test_protein_must_be_non_negative(self):
        """Test that protein must be non-negative."""
        with pytest.raises(ValueError, match="Protein must be non-negative"):
            MacroSplit(protein_g=-10, carbs_g=250, fat_g=70)

    def test_carbs_must_be_non_negative(self):
        """Test that carbs must be non-negative."""
        with pytest.raises(ValueError, match="Carbs must be non-negative"):
            MacroSplit(protein_g=150, carbs_g=-10, fat_g=70)

    def test_fat_must_be_non_negative(self):
        """Test that fat must be non-negative."""
        with pytest.raises(ValueError, match="Fat must be non-negative"):
            MacroSplit(protein_g=150, carbs_g=250, fat_g=-10)

    def test_total_calories(self):
        """Test total calories calculation."""
        macros = MacroSplit(protein_g=150, carbs_g=250, fat_g=70)

        # 150*4 + 250*4 + 70*9 = 600 + 1000 + 630 = 2230
        assert macros.total_calories() == 2230.0

    def test_protein_percentage(self):
        """Test protein percentage calculation."""
        macros = MacroSplit(protein_g=150, carbs_g=250, fat_g=70)

        # (150*4) / 2230 * 100 = 26.9%
        assert abs(macros.protein_percentage() - 26.9) < 0.1

    def test_carbs_percentage(self):
        """Test carbs percentage calculation."""
        macros = MacroSplit(protein_g=150, carbs_g=250, fat_g=70)

        # (250*4) / 2230 * 100 = 44.8%
        assert abs(macros.carbs_percentage() - 44.8) < 0.1

    def test_fat_percentage(self):
        """Test fat percentage calculation."""
        macros = MacroSplit(protein_g=150, carbs_g=250, fat_g=70)

        # (70*9) / 2230 * 100 = 28.3%
        assert abs(macros.fat_percentage() - 28.3) < 0.1

    def test_percentages_sum_to_100(self):
        """Test that percentages sum to 100%."""
        macros = MacroSplit(protein_g=150, carbs_g=250, fat_g=70)

        total = macros.protein_percentage() + macros.carbs_percentage() + macros.fat_percentage()

        assert abs(total - 100.0) < 0.1

    def test_str_representation(self):
        """Test string representation."""
        macros = MacroSplit(protein_g=150, carbs_g=250, fat_g=70)

        assert str(macros) == "150P / 250C / 70F"

    def test_repr_representation(self):
        """Test repr representation."""
        macros = MacroSplit(protein_g=150, carbs_g=250, fat_g=70)

        assert repr(macros) == ("MacroSplit(protein_g=150, carbs_g=250, fat_g=70)")
