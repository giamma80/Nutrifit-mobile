"""Unit tests for nutritional profile factory."""

from datetime import date

from domain.nutritional_profile.core.factories import NutritionalProfileFactory
from domain.nutritional_profile.core.value_objects import (
    ActivityLevel,
    Goal,
    UserData,
    BMR,
    TDEE,
    MacroSplit,
)


class TestNutritionalProfileFactory:
    """Test NutritionalProfileFactory."""

    def setup_method(self):
        """Set up test fixtures."""
        self.user_data = UserData(
            weight=80.0, height=180.0, age=30, sex="M", activity_level=ActivityLevel.MODERATE
        )
        self.goal = Goal.CUT
        self.bmr = BMR(1800.0)
        self.tdee = TDEE(2790.0)
        self.calories_target = 2290.0
        self.macro_split = MacroSplit(protein_g=176, carbs_g=248, fat_g=63)

    def test_create_profile_with_initial_progress(self):
        """Test creating a profile with initial progress record."""
        today = date.today()

        profile = NutritionalProfileFactory.create(
            user_id="user123",
            user_data=self.user_data,
            goal=self.goal,
            bmr=self.bmr,
            tdee=self.tdee,
            calories_target=self.calories_target,
            macro_split=self.macro_split,
            initial_weight=80.0,
            initial_date=today,
        )

        assert profile.user_id == "user123"
        assert profile.user_data.weight == 80.0
        assert profile.goal == Goal.CUT
        assert profile.bmr.value == 1800.0
        assert profile.tdee.value == 2790.0
        assert profile.calories_target == 2290.0
        assert len(profile.progress_history) == 1
        assert profile.progress_history[0].weight == 80.0
        assert profile.progress_history[0].date == today
        assert profile.progress_history[0].notes == "Initial measurement"

    def test_create_generates_profile_id(self):
        """Test that factory generates profile ID."""
        today = date.today()

        profile = NutritionalProfileFactory.create(
            user_id="user123",
            user_data=self.user_data,
            goal=self.goal,
            bmr=self.bmr,
            tdee=self.tdee,
            calories_target=self.calories_target,
            macro_split=self.macro_split,
            initial_weight=80.0,
            initial_date=today,
        )

        assert profile.profile_id is not None

    def test_create_with_different_goals(self):
        """Test creating profiles with different goals."""
        today = date.today()

        # Test CUT goal (TDEE - 500)
        cut_macro = MacroSplit(protein_g=176, carbs_g=248, fat_g=63)  # ~2290 kcal
        cut_profile = NutritionalProfileFactory.create(
            user_id="user123",
            user_data=self.user_data,
            goal=Goal.CUT,
            bmr=self.bmr,
            tdee=self.tdee,
            calories_target=2290.0,
            macro_split=cut_macro,
            initial_weight=80.0,
            initial_date=today,
        )
        assert cut_profile.goal == Goal.CUT

        # Test MAINTAIN goal (TDEE + 0)
        maintain_macro = MacroSplit(protein_g=144, carbs_g=324, fat_g=93)  # ~2790 kcal
        maintain_profile = NutritionalProfileFactory.create(
            user_id="user123",
            user_data=self.user_data,
            goal=Goal.MAINTAIN,
            bmr=self.bmr,
            tdee=self.tdee,
            calories_target=2790.0,
            macro_split=maintain_macro,
            initial_weight=80.0,
            initial_date=today,
        )
        assert maintain_profile.goal == Goal.MAINTAIN

        # Test BULK goal (TDEE + 300)
        # 3090 kcal: 160g protein (640) + 68g fat (612) + 459g carbs (1836)
        bulk_macro = MacroSplit(protein_g=160, carbs_g=459, fat_g=68)
        bulk_profile = NutritionalProfileFactory.create(
            user_id="user123",
            user_data=self.user_data,
            goal=Goal.BULK,
            bmr=self.bmr,
            tdee=self.tdee,
            calories_target=3090.0,
            macro_split=bulk_macro,
            initial_weight=80.0,
            initial_date=today,
        )
        assert bulk_profile.goal == Goal.BULK

    def test_create_without_progress(self):
        """Test creating profile without initial progress."""
        profile = NutritionalProfileFactory.create_without_progress(
            user_id="user123",
            user_data=self.user_data,
            goal=self.goal,
            bmr=self.bmr,
            tdee=self.tdee,
            calories_target=self.calories_target,
            macro_split=self.macro_split,
        )

        assert profile.user_id == "user123"
        assert len(profile.progress_history) == 0

    def test_create_without_progress_generates_id(self):
        """Test that create_without_progress generates profile ID."""
        profile = NutritionalProfileFactory.create_without_progress(
            user_id="user123",
            user_data=self.user_data,
            goal=self.goal,
            bmr=self.bmr,
            tdee=self.tdee,
            calories_target=self.calories_target,
            macro_split=self.macro_split,
        )

        assert profile.profile_id is not None

    def test_create_with_user_data(self):
        """Test that factory uses provided user data."""
        today = date.today()

        profile = NutritionalProfileFactory.create(
            user_id="user456",
            user_data=self.user_data,
            goal=self.goal,
            bmr=self.bmr,
            tdee=self.tdee,
            calories_target=self.calories_target,
            macro_split=self.macro_split,
            initial_weight=75.0,
            initial_date=today,
        )

        assert profile.user_data.weight == 80.0  # From UserData fixture
        assert profile.user_data.height == 180.0
        assert profile.user_data.age == 30
        assert profile.user_data.sex == "M"
        assert profile.user_data.activity_level == ActivityLevel.MODERATE

    def test_create_with_macro_split(self):
        """Test that factory stores macro split."""
        today = date.today()

        profile = NutritionalProfileFactory.create(
            user_id="user123",
            user_data=self.user_data,
            goal=self.goal,
            bmr=self.bmr,
            tdee=self.tdee,
            calories_target=self.calories_target,
            macro_split=self.macro_split,
            initial_weight=80.0,
            initial_date=today,
        )

        assert profile.macro_split.protein_g == 176
        assert profile.macro_split.carbs_g == 248
        assert profile.macro_split.fat_g == 63

    def test_create_with_calculations(self):
        """Test that factory stores BMR, TDEE, and calorie target."""
        today = date.today()

        profile = NutritionalProfileFactory.create(
            user_id="user123",
            user_data=self.user_data,
            goal=self.goal,
            bmr=self.bmr,
            tdee=self.tdee,
            calories_target=self.calories_target,
            macro_split=self.macro_split,
            initial_weight=80.0,
            initial_date=today,
        )

        assert profile.bmr.value == 1800.0
        assert profile.tdee.value == 2790.0
        assert profile.calories_target == 2290.0
