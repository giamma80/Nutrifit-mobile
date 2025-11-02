"""Unit tests for nutritional profile entities."""

from datetime import date, timedelta

import pytest

from domain.nutritional_profile.core.entities import (
    NutritionalProfile,
    ProgressRecord,
)
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


class TestProgressRecord:
    """Test ProgressRecord entity."""

    def test_create_progress_record(self):
        """Test creating a progress record."""
        profile_id = ProfileId.generate()
        record = ProgressRecord.create(profile_id=profile_id, date=date.today(), weight=75.5)

        assert record.profile_id == profile_id
        assert record.date == date.today()
        assert record.weight == 75.5
        assert record.consumed_calories is None

    def test_create_with_calories(self):
        """Test creating record with consumed calories."""
        profile_id = ProfileId.generate()
        record = ProgressRecord.create(
            profile_id=profile_id, date=date.today(), weight=75.5, consumed_calories=2200.0
        )

        assert record.consumed_calories == 2200.0

    def test_create_with_notes(self):
        """Test creating record with notes."""
        profile_id = ProfileId.generate()
        record = ProgressRecord.create(
            profile_id=profile_id, date=date.today(), weight=75.5, notes="Felt great today"
        )

        assert record.notes == "Felt great today"

    def test_update_consumed_calories(self):
        """Test updating consumed calories."""
        profile_id = ProfileId.generate()
        record = ProgressRecord.create(profile_id=profile_id, date=date.today(), weight=75.5)

        record.update_consumed_calories(2200.0)

        assert record.consumed_calories == 2200.0

    def test_update_consumed_calories_negative_raises(self):
        """Test that negative calories raises error."""
        profile_id = ProfileId.generate()
        record = ProgressRecord.create(profile_id=profile_id, date=date.today(), weight=75.5)

        with pytest.raises(ValueError, match="non-negative"):
            record.update_consumed_calories(-100.0)

    def test_calorie_delta_with_target(self):
        """Test calorie delta calculation."""
        profile_id = ProfileId.generate()
        record = ProgressRecord.create(
            profile_id=profile_id, date=date.today(), weight=75.5, consumed_calories=2300.0
        )

        target = 2000.0
        delta = record.calorie_delta(target)

        assert delta == 300.0  # 2300 - 2000

    def test_calorie_delta_none_consumed(self):
        """Test calorie delta when consumed is None."""
        profile_id = ProfileId.generate()
        record = ProgressRecord.create(profile_id=profile_id, date=date.today(), weight=75.5)

        delta = record.calorie_delta(2000.0)

        assert delta is None

    def test_is_on_track_within_tolerance(self):
        """Test on-track check within tolerance."""
        profile_id = ProfileId.generate()
        record = ProgressRecord.create(
            profile_id=profile_id, date=date.today(), weight=75.5, consumed_calories=2050.0
        )

        # Within 10% of 2000 (1800-2200)
        assert record.is_on_track(2000.0, tolerance_percentage=0.10)

    def test_is_on_track_outside_tolerance(self):
        """Test on-track check outside tolerance."""
        profile_id = ProfileId.generate()
        record = ProgressRecord.create(
            profile_id=profile_id, date=date.today(), weight=75.5, consumed_calories=2500.0
        )

        # Outside 10% of 2000 (1800-2200)
        assert not record.is_on_track(2000.0, tolerance_percentage=0.10)

    def test_is_on_track_none_consumed(self):
        """Test on-track returns None when consumed is None."""
        profile_id = ProfileId.generate()
        record = ProgressRecord.create(profile_id=profile_id, date=date.today(), weight=75.5)

        assert record.is_on_track(2000.0) is None

    def test_weight_must_be_positive(self):
        """Test that weight must be positive."""
        profile_id = ProfileId.generate()

        with pytest.raises(ValueError, match="Weight must be positive"):
            ProgressRecord(
                record_id=profile_id.value, profile_id=profile_id, date=date.today(), weight=-75.5
            )

    def test_consumed_calories_negative_raises(self):
        """Test that negative consumed calories raises."""
        profile_id = ProfileId.generate()

        with pytest.raises(ValueError, match="non-negative"):
            ProgressRecord(
                record_id=profile_id.value,
                profile_id=profile_id,
                date=date.today(),
                weight=75.5,
                consumed_calories=-100.0,
            )


class TestNutritionalProfile:
    """Test NutritionalProfile aggregate root."""

    def setup_method(self):
        """Set up test fixtures."""
        self.profile_id = ProfileId.generate()
        self.user_id = "user123"
        self.user_data = UserData(
            weight=80.0, height=180.0, age=30, sex="M", activity_level=ActivityLevel.MODERATE
        )
        self.goal = Goal.CUT
        self.bmr = BMR(1800.0)
        self.tdee = TDEE(2790.0)
        self.calories_target = 2290.0
        self.macro_split = MacroSplit(protein_g=176, carbs_g=248, fat_g=63)

    def test_create_nutritional_profile(self):
        """Test creating a nutritional profile."""
        profile = NutritionalProfile(
            profile_id=self.profile_id,
            user_id=self.user_id,
            user_data=self.user_data,
            goal=self.goal,
            bmr=self.bmr,
            tdee=self.tdee,
            calories_target=self.calories_target,
            macro_split=self.macro_split,
        )

        assert profile.profile_id == self.profile_id
        assert profile.user_id == self.user_id
        assert profile.goal == Goal.CUT
        assert len(profile.progress_history) == 0

    def test_empty_user_id_raises(self):
        """Test that empty user ID raises error."""
        with pytest.raises(InvalidUserDataError, match="User ID"):
            NutritionalProfile(
                profile_id=self.profile_id,
                user_id="",
                user_data=self.user_data,
                goal=self.goal,
                bmr=self.bmr,
                tdee=self.tdee,
                calories_target=self.calories_target,
                macro_split=self.macro_split,
            )

    def test_negative_calories_target_raises(self):
        """Test that negative calories target raises error."""
        with pytest.raises(InvalidUserDataError, match="positive"):
            NutritionalProfile(
                profile_id=self.profile_id,
                user_id=self.user_id,
                user_data=self.user_data,
                goal=self.goal,
                bmr=self.bmr,
                tdee=self.tdee,
                calories_target=-100.0,
                macro_split=self.macro_split,
            )

    def test_macro_split_mismatch_raises(self):
        """Test that macro/calorie mismatch raises error."""
        # Macro split totaling 3000 kcal vs 2290 target (>5%)
        bad_macros = MacroSplit(protein_g=200, carbs_g=300, fat_g=100)

        with pytest.raises(InvalidUserDataError, match="does not match"):
            NutritionalProfile(
                profile_id=self.profile_id,
                user_id=self.user_id,
                user_data=self.user_data,
                goal=self.goal,
                bmr=self.bmr,
                tdee=self.tdee,
                calories_target=self.calories_target,
                macro_split=bad_macros,
            )

    def test_update_user_data_weight(self):
        """Test updating user weight."""
        profile = NutritionalProfile(
            profile_id=self.profile_id,
            user_id=self.user_id,
            user_data=self.user_data,
            goal=self.goal,
            bmr=self.bmr,
            tdee=self.tdee,
            calories_target=self.calories_target,
            macro_split=self.macro_split,
        )

        profile.update_user_data(weight=78.0)

        assert profile.user_data.weight == 78.0
        assert profile.user_data.height == 180.0  # unchanged

    def test_update_user_data_activity(self):
        """Test updating activity level."""
        profile = NutritionalProfile(
            profile_id=self.profile_id,
            user_id=self.user_id,
            user_data=self.user_data,
            goal=self.goal,
            bmr=self.bmr,
            tdee=self.tdee,
            calories_target=self.calories_target,
            macro_split=self.macro_split,
        )

        profile.update_user_data(activity_level="active")

        assert profile.user_data.activity_level == ActivityLevel.ACTIVE

    def test_update_goal(self):
        """Test updating goal."""
        profile = NutritionalProfile(
            profile_id=self.profile_id,
            user_id=self.user_id,
            user_data=self.user_data,
            goal=self.goal,
            bmr=self.bmr,
            tdee=self.tdee,
            calories_target=self.calories_target,
            macro_split=self.macro_split,
        )

        profile.update_goal(Goal.MAINTAIN)

        assert profile.goal == Goal.MAINTAIN

    def test_update_calculations(self):
        """Test updating calculated values."""
        profile = NutritionalProfile(
            profile_id=self.profile_id,
            user_id=self.user_id,
            user_data=self.user_data,
            goal=self.goal,
            bmr=self.bmr,
            tdee=self.tdee,
            calories_target=self.calories_target,
            macro_split=self.macro_split,
        )

        new_bmr = BMR(1850.0)
        new_tdee = TDEE(2867.5)
        new_target = 2367.5
        new_macros = MacroSplit(protein_g=180, carbs_g=255, fat_g=65)

        profile.update_calculations(
            bmr=new_bmr, tdee=new_tdee, calories_target=new_target, macro_split=new_macros
        )

        assert profile.bmr.value == 1850.0
        assert profile.tdee.value == 2867.5
        assert profile.calories_target == 2367.5

    def test_record_progress(self):
        """Test recording progress."""
        profile = NutritionalProfile(
            profile_id=self.profile_id,
            user_id=self.user_id,
            user_data=self.user_data,
            goal=self.goal,
            bmr=self.bmr,
            tdee=self.tdee,
            calories_target=self.calories_target,
            macro_split=self.macro_split,
        )

        record = profile.record_progress(
            measurement_date=date.today(), weight=79.5, consumed_calories=2200.0
        )

        assert len(profile.progress_history) == 1
        assert profile.progress_history[0].weight == 79.5
        assert record.weight == 79.5

    def test_get_progress_by_date(self):
        """Test getting progress by date."""
        today = date.today()
        profile = NutritionalProfile(
            profile_id=self.profile_id,
            user_id=self.user_id,
            user_data=self.user_data,
            goal=self.goal,
            bmr=self.bmr,
            tdee=self.tdee,
            calories_target=self.calories_target,
            macro_split=self.macro_split,
        )

        profile.record_progress(measurement_date=today, weight=79.5)

        found = profile.get_progress_by_date(today)

        assert found is not None
        assert found.weight == 79.5

    def test_get_progress_by_date_not_found(self):
        """Test getting progress when date not found."""
        profile = NutritionalProfile(
            profile_id=self.profile_id,
            user_id=self.user_id,
            user_data=self.user_data,
            goal=self.goal,
            bmr=self.bmr,
            tdee=self.tdee,
            calories_target=self.calories_target,
            macro_split=self.macro_split,
        )

        found = profile.get_progress_by_date(date.today())

        assert found is None

    def test_get_progress_range(self):
        """Test getting progress range."""
        today = date.today()
        yesterday = today - timedelta(days=1)

        profile = NutritionalProfile(
            profile_id=self.profile_id,
            user_id=self.user_id,
            user_data=self.user_data,
            goal=self.goal,
            bmr=self.bmr,
            tdee=self.tdee,
            calories_target=self.calories_target,
            macro_split=self.macro_split,
        )

        profile.record_progress(measurement_date=yesterday, weight=80.0)
        profile.record_progress(measurement_date=today, weight=79.5)

        range_records = profile.get_progress_range(yesterday, today)

        assert len(range_records) == 2
        assert range_records[0].date == yesterday
        assert range_records[1].date == today

    def test_calculate_weight_delta(self):
        """Test calculating weight delta."""
        week_ago = date.today() - timedelta(days=7)
        today = date.today()

        profile = NutritionalProfile(
            profile_id=self.profile_id,
            user_id=self.user_id,
            user_data=self.user_data,
            goal=self.goal,
            bmr=self.bmr,
            tdee=self.tdee,
            calories_target=self.calories_target,
            macro_split=self.macro_split,
        )

        profile.record_progress(measurement_date=week_ago, weight=81.0)
        profile.record_progress(measurement_date=today, weight=79.5)

        delta = profile.calculate_weight_delta(week_ago, today)

        assert delta == -1.5  # 79.5 - 81.0

    def test_calculate_weight_delta_insufficient_data(self):
        """Test weight delta with insufficient data."""
        profile = NutritionalProfile(
            profile_id=self.profile_id,
            user_id=self.user_id,
            user_data=self.user_data,
            goal=self.goal,
            bmr=self.bmr,
            tdee=self.tdee,
            calories_target=self.calories_target,
            macro_split=self.macro_split,
        )

        today = date.today()
        profile.record_progress(measurement_date=today, weight=80.0)

        # Only 1 record, need at least 2
        delta = profile.calculate_weight_delta(today, today)

        assert delta is None

    def test_calculate_target_weight_delta(self):
        """Test calculating target weight change."""
        profile = NutritionalProfile(
            profile_id=self.profile_id,
            user_id=self.user_id,
            user_data=self.user_data,
            goal=self.goal,
            bmr=self.bmr,
            tdee=self.tdee,
            calories_target=2290.0,  # -500 deficit
            macro_split=self.macro_split,
        )

        # Formula: (tdee - target) / 7700 * days
        # (2790 - 2290) / 7700 * 7 = 500 / 7700 * 7 = 0.45 kg
        target_delta = profile.calculate_target_weight_delta(7)

        assert abs(target_delta - 0.45) < 0.01  # Positive because tdee > target

    def test_average_daily_calories(self):
        """Test calculating average daily calories."""
        start = date.today() - timedelta(days=2)
        end = date.today()

        profile = NutritionalProfile(
            profile_id=self.profile_id,
            user_id=self.user_id,
            user_data=self.user_data,
            goal=self.goal,
            bmr=self.bmr,
            tdee=self.tdee,
            calories_target=self.calories_target,
            macro_split=self.macro_split,
        )

        profile.record_progress(measurement_date=start, weight=80.0, consumed_calories=2100.0)
        profile.record_progress(
            measurement_date=start + timedelta(days=1), weight=79.5, consumed_calories=2200.0
        )
        profile.record_progress(measurement_date=end, weight=79.0, consumed_calories=2300.0)

        avg = profile.average_daily_calories(start, end)

        assert avg == 2200.0  # (2100 + 2200 + 2300) / 3

    def test_average_daily_calories_no_data(self):
        """Test average when no calorie data."""
        profile = NutritionalProfile(
            profile_id=self.profile_id,
            user_id=self.user_id,
            user_data=self.user_data,
            goal=self.goal,
            bmr=self.bmr,
            tdee=self.tdee,
            calories_target=self.calories_target,
            macro_split=self.macro_split,
        )

        today = date.today()
        profile.record_progress(measurement_date=today, weight=80.0)

        avg = profile.average_daily_calories(today, today)

        assert avg is None

    def test_days_on_track(self):
        """Test counting days on track."""
        start = date.today() - timedelta(days=2)
        end = date.today()

        profile = NutritionalProfile(
            profile_id=self.profile_id,
            user_id=self.user_id,
            user_data=self.user_data,
            goal=self.goal,
            bmr=self.bmr,
            tdee=self.tdee,
            calories_target=2290.0,
            macro_split=self.macro_split,
        )

        # Day 1: on track (2290, within 10% tolerance: 2061-2519)
        profile.record_progress(measurement_date=start, weight=80.0, consumed_calories=2290.0)
        # Day 2: off track (2600, outside 10% tolerance)
        profile.record_progress(
            measurement_date=start + timedelta(days=1), weight=79.5, consumed_calories=2600.0
        )
        # Day 3: on track (2250, within tolerance)
        profile.record_progress(measurement_date=end, weight=79.0, consumed_calories=2250.0)

        on_track = profile.days_on_track(start, end, tolerance_percentage=0.10)

        assert on_track == 2  # 2 out of 3 days on track
