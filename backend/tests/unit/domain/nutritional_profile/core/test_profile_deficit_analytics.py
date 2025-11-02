"""Unit tests for NutritionalProfile deficit tracking analytics."""

from datetime import date, timedelta

import pytest

from domain.nutritional_profile.core.entities.nutritional_profile import (
    NutritionalProfile,
)
from domain.nutritional_profile.core.value_objects.activity_level import (
    ActivityLevel,
)
from domain.nutritional_profile.core.value_objects.bmr import BMR
from domain.nutritional_profile.core.value_objects.goal import Goal
from domain.nutritional_profile.core.value_objects.macro_split import (
    MacroSplit,
)
from domain.nutritional_profile.core.value_objects.profile_id import ProfileId
from domain.nutritional_profile.core.value_objects.tdee import TDEE
from domain.nutritional_profile.core.value_objects.user_data import UserData


@pytest.fixture
def sample_profile() -> NutritionalProfile:
    """Create sample profile for testing."""
    return NutritionalProfile(
        profile_id=ProfileId.generate(),
        user_id="user123",
        user_data=UserData(
            weight=80.0,
            height=180.0,
            age=30,
            sex="M",
            activity_level=ActivityLevel.MODERATE,
        ),
        goal=Goal.CUT,
        bmr=BMR(value=1780.0),
        tdee=TDEE(value=2759.0),
        calories_target=2259.0,
        macro_split=MacroSplit(protein_g=176, carbs_g=248, fat_g=63),
    )


def test_days_deficit_on_track_all_on_track(
    sample_profile: NutritionalProfile,
) -> None:
    """Test days_deficit_on_track with all days on track."""
    start = date.today() - timedelta(days=2)
    end = date.today()

    # Day 1: -500 deficit (target: -500)
    sample_profile.record_progress(measurement_date=start, weight=80.0, consumed_calories=2300.0)
    sample_profile.progress_history[-1].update_burned_calories(
        bmr_calories=1800.0, active_calories=1000.0
    )  # Total: 2800

    # Day 2: -480 deficit (within 50 kcal tolerance)
    sample_profile.record_progress(
        measurement_date=start + timedelta(days=1),
        weight=79.8,
        consumed_calories=2320.0,
    )
    sample_profile.progress_history[-1].update_burned_calories(
        bmr_calories=1800.0, active_calories=1000.0
    )  # Total: 2800

    # Day 3: -520 deficit (within tolerance)
    sample_profile.record_progress(measurement_date=end, weight=79.5, consumed_calories=2280.0)
    sample_profile.progress_history[-1].update_burned_calories(
        bmr_calories=1800.0, active_calories=1000.0
    )  # Total: 2800

    on_track = sample_profile.days_deficit_on_track(start, end, tolerance_kcal=50.0)

    assert on_track == 3


def test_days_deficit_on_track_partial(sample_profile: NutritionalProfile) -> None:
    """Test days_deficit_on_track with some days off track."""
    start = date.today() - timedelta(days=2)
    end = date.today()

    # Day 1: -500 deficit ✅ on track
    sample_profile.record_progress(measurement_date=start, weight=80.0, consumed_calories=2300.0)
    sample_profile.progress_history[-1].update_burned_calories(
        bmr_calories=1800.0, active_calories=1000.0
    )

    # Day 2: -200 deficit ❌ off track (too small deficit)
    sample_profile.record_progress(
        measurement_date=start + timedelta(days=1),
        weight=79.8,
        consumed_calories=2600.0,
    )
    sample_profile.progress_history[-1].update_burned_calories(
        bmr_calories=1800.0, active_calories=1000.0
    )

    # Day 3: -800 deficit ❌ off track (too large deficit)
    sample_profile.record_progress(measurement_date=end, weight=79.5, consumed_calories=2000.0)
    sample_profile.progress_history[-1].update_burned_calories(
        bmr_calories=1800.0, active_calories=1000.0
    )

    on_track = sample_profile.days_deficit_on_track(start, end, tolerance_kcal=50.0)

    assert on_track == 1  # Only day 1 on track


def test_days_deficit_on_track_varying_activity(
    sample_profile: NutritionalProfile,
) -> None:
    """Test deficit tracking with varying daily activity."""
    start = date.today() - timedelta(days=2)
    end = date.today()

    # Day 1: Low activity, -500 deficit
    sample_profile.record_progress(measurement_date=start, weight=80.0, consumed_calories=1800.0)
    sample_profile.progress_history[-1].update_burned_calories(
        bmr_calories=1800.0, active_calories=500.0
    )  # Total: 2300, deficit: -500 ✅

    # Day 2: High activity, still -500 deficit
    sample_profile.record_progress(
        measurement_date=start + timedelta(days=1),
        weight=79.8,
        consumed_calories=2800.0,
    )
    sample_profile.progress_history[-1].update_burned_calories(
        bmr_calories=1800.0, active_calories=1500.0
    )  # Total: 3300, deficit: -500 ✅

    # Day 3: Rest day, -500 deficit
    sample_profile.record_progress(measurement_date=end, weight=79.5, consumed_calories=1300.0)
    sample_profile.progress_history[-1].update_burned_calories(
        bmr_calories=1800.0, active_calories=0.0
    )  # Total: 1800, deficit: -500 ✅

    on_track = sample_profile.days_deficit_on_track(start, end, tolerance_kcal=50.0)

    assert on_track == 3  # All days maintain deficit despite activity


def test_days_deficit_on_track_bulk_goal() -> None:
    """Test deficit tracking for bulk goal (surplus)."""
    profile = NutritionalProfile(
        profile_id=ProfileId.generate(),
        user_id="user123",
        user_data=UserData(
            weight=80.0,
            height=180.0,
            age=30,
            sex="M",
            activity_level=ActivityLevel.MODERATE,
        ),
        goal=Goal.BULK,  # +300 surplus target
        bmr=BMR(value=1780.0),
        tdee=TDEE(value=2759.0),
        calories_target=3059.0,
        macro_split=MacroSplit(protein_g=160, carbs_g=452, fat_g=68),
    )

    start = date.today()

    # Day 1: +300 surplus ✅
    profile.record_progress(measurement_date=start, weight=80.0, consumed_calories=3100.0)
    profile.progress_history[-1].update_burned_calories(
        bmr_calories=1800.0, active_calories=1000.0
    )  # Total: 2800, surplus: +300

    on_track = profile.days_deficit_on_track(start, start, tolerance_kcal=50.0)

    assert on_track == 1


def test_days_deficit_on_track_incomplete_data(
    sample_profile: NutritionalProfile,
) -> None:
    """Test with incomplete calorie data."""
    start = date.today() - timedelta(days=1)
    end = date.today()

    # Day 1: Complete data
    sample_profile.record_progress(measurement_date=start, weight=80.0, consumed_calories=2300.0)
    sample_profile.progress_history[-1].update_burned_calories(
        bmr_calories=1800.0, active_calories=1000.0
    )

    # Day 2: Missing burned calories
    sample_profile.record_progress(measurement_date=end, weight=79.8, consumed_calories=2300.0)
    # No update_burned_calories called

    on_track = sample_profile.days_deficit_on_track(start, end, tolerance_kcal=50.0)

    assert on_track == 1  # Only day 1 counted


def test_average_deficit_consistent(sample_profile: NutritionalProfile) -> None:
    """Test average_deficit with consistent deficit."""
    start = date.today() - timedelta(days=2)
    end = date.today()

    for i in range(3):
        measurement_date = start + timedelta(days=i)
        sample_profile.record_progress(
            measurement_date=measurement_date,
            weight=80.0 - i * 0.2,
            consumed_calories=2300.0,
        )
        sample_profile.progress_history[-1].update_burned_calories(
            bmr_calories=1800.0, active_calories=1000.0
        )  # -500 deficit each day

    avg_deficit = sample_profile.average_deficit(start, end)

    assert avg_deficit == -500.0


def test_average_deficit_varying(sample_profile: NutritionalProfile) -> None:
    """Test average_deficit with varying deficits."""
    start = date.today() - timedelta(days=2)
    end = date.today()

    # Day 1: -400 deficit
    sample_profile.record_progress(measurement_date=start, weight=80.0, consumed_calories=2400.0)
    sample_profile.progress_history[-1].update_burned_calories(
        bmr_calories=1800.0, active_calories=1000.0
    )

    # Day 2: -500 deficit
    sample_profile.record_progress(
        measurement_date=start + timedelta(days=1),
        weight=79.8,
        consumed_calories=2300.0,
    )
    sample_profile.progress_history[-1].update_burned_calories(
        bmr_calories=1800.0, active_calories=1000.0
    )

    # Day 3: -600 deficit
    sample_profile.record_progress(measurement_date=end, weight=79.5, consumed_calories=2200.0)
    sample_profile.progress_history[-1].update_burned_calories(
        bmr_calories=1800.0, active_calories=1000.0
    )

    avg_deficit = sample_profile.average_deficit(start, end)

    assert avg_deficit == -500.0  # (-400 + -500 + -600) / 3


def test_average_deficit_no_data(sample_profile: NutritionalProfile) -> None:
    """Test average_deficit with no calorie data."""
    start = date.today()
    end = date.today()

    # Record without calorie data
    sample_profile.record_progress(measurement_date=start, weight=80.0, consumed_calories=None)

    avg_deficit = sample_profile.average_deficit(start, end)

    assert avg_deficit is None


def test_average_deficit_partial_data(sample_profile: NutritionalProfile) -> None:
    """Test average_deficit with some incomplete data."""
    start = date.today() - timedelta(days=1)
    end = date.today()

    # Day 1: Complete data (-500)
    sample_profile.record_progress(measurement_date=start, weight=80.0, consumed_calories=2300.0)
    sample_profile.progress_history[-1].update_burned_calories(
        bmr_calories=1800.0, active_calories=1000.0
    )

    # Day 2: Incomplete (missing burned calories)
    sample_profile.record_progress(measurement_date=end, weight=79.8, consumed_calories=2300.0)

    avg_deficit = sample_profile.average_deficit(start, end)

    # Should average only day 1 (complete data)
    assert avg_deficit == -500.0


def test_goal_target_deficit() -> None:
    """Test Goal.target_deficit() returns correct values."""
    assert Goal.CUT.target_deficit() == -500
    assert Goal.MAINTAIN.target_deficit() == 0
    assert Goal.BULK.target_deficit() == +300
