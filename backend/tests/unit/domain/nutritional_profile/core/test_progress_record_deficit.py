"""Unit tests for ProgressRecord dynamic deficit tracking."""

from datetime import date

import pytest

from domain.nutritional_profile.core.entities.progress_record import (
    ProgressRecord,
)
from domain.nutritional_profile.core.value_objects.profile_id import ProfileId


@pytest.fixture
def profile_id() -> ProfileId:
    """Create sample profile ID."""
    return ProfileId.generate()


def test_update_burned_calories(profile_id: ProfileId) -> None:
    """Test updating burned calories."""
    record = ProgressRecord.create(
        profile_id=profile_id,
        date=date(2024, 1, 1),
        weight=80.0,
    )

    record.update_burned_calories(bmr_calories=1800.0, active_calories=500.0)

    assert record.calories_burned_bmr == 1800.0
    assert record.calories_burned_active == 500.0


def test_update_burned_calories_validation(profile_id: ProfileId) -> None:
    """Test burned calories validation."""
    record = ProgressRecord.create(
        profile_id=profile_id,
        date=date(2024, 1, 1),
        weight=80.0,
    )

    with pytest.raises(ValueError, match="BMR calories must be non-negative"):
        record.update_burned_calories(bmr_calories=-100.0, active_calories=500.0)

    with pytest.raises(ValueError, match="Active calories must be non-negative"):
        record.update_burned_calories(bmr_calories=1800.0, active_calories=-50.0)


def test_calories_burned_total(profile_id: ProfileId) -> None:
    """Test total burned calories calculation."""
    record = ProgressRecord.create(
        profile_id=profile_id,
        date=date(2024, 1, 1),
        weight=80.0,
    )

    # No data initially
    assert record.calories_burned_total is None

    # Partial data (only BMR)
    record.calories_burned_bmr = 1800.0
    assert record.calories_burned_total is None

    # Complete data
    record.calories_burned_active = 500.0
    assert record.calories_burned_total == 2300.0


def test_calorie_balance_deficit(profile_id: ProfileId) -> None:
    """Test calorie balance calculation for deficit."""
    record = ProgressRecord.create(
        profile_id=profile_id,
        date=date(2024, 1, 1),
        weight=80.0,
        consumed_calories=1800.0,
    )

    record.update_burned_calories(bmr_calories=1800.0, active_calories=500.0)

    # Consumed 1800, burned 2300 = -500 deficit
    assert record.calorie_balance == -500.0


def test_calorie_balance_surplus(profile_id: ProfileId) -> None:
    """Test calorie balance calculation for surplus."""
    record = ProgressRecord.create(
        profile_id=profile_id,
        date=date(2024, 1, 1),
        weight=80.0,
        consumed_calories=2800.0,
    )

    record.update_burned_calories(bmr_calories=1800.0, active_calories=500.0)

    # Consumed 2800, burned 2300 = +500 surplus
    assert record.calorie_balance == 500.0


def test_calorie_balance_incomplete_data(profile_id: ProfileId) -> None:
    """Test calorie balance returns None if data incomplete."""
    record = ProgressRecord.create(
        profile_id=profile_id,
        date=date(2024, 1, 1),
        weight=80.0,
    )

    # No consumed calories
    assert record.calorie_balance is None

    # No burned calories
    record.consumed_calories = 2000.0
    assert record.calorie_balance is None

    # Only BMR, no active
    record.calories_burned_bmr = 1800.0
    assert record.calorie_balance is None

    # Complete data
    record.calories_burned_active = 500.0
    assert record.calorie_balance == -300.0


def test_is_deficit_on_track_cut(profile_id: ProfileId) -> None:
    """Test deficit tracking for cut goal."""
    record = ProgressRecord.create(
        profile_id=profile_id,
        date=date(2024, 1, 1),
        weight=80.0,
        consumed_calories=2300.0,
    )

    record.update_burned_calories(bmr_calories=1800.0, active_calories=1000.0)

    # Consumed 2300, burned 2800 = -500 deficit
    # Target: -500, tolerance: 50
    assert record.is_deficit_on_track(-500.0, tolerance_kcal=50.0) is True

    # Within tolerance
    record.consumed_calories = 2750.0  # -50 deficit
    assert record.is_deficit_on_track(-500.0, tolerance_kcal=500.0) is True

    # Outside tolerance
    record.consumed_calories = 2750.0  # -50 deficit
    assert record.is_deficit_on_track(-500.0, tolerance_kcal=50.0) is False


def test_is_deficit_on_track_bulk(profile_id: ProfileId) -> None:
    """Test deficit tracking for bulk goal."""
    record = ProgressRecord.create(
        profile_id=profile_id,
        date=date(2024, 1, 1),
        weight=80.0,
        consumed_calories=2600.0,
    )

    record.update_burned_calories(bmr_calories=1800.0, active_calories=500.0)

    # Consumed 2600, burned 2300 = +300 surplus
    # Target: +300, tolerance: 50
    assert record.is_deficit_on_track(+300.0, tolerance_kcal=50.0) is True


def test_is_deficit_on_track_maintain(profile_id: ProfileId) -> None:
    """Test deficit tracking for maintenance goal."""
    record = ProgressRecord.create(
        profile_id=profile_id,
        date=date(2024, 1, 1),
        weight=80.0,
        consumed_calories=2300.0,
    )

    record.update_burned_calories(bmr_calories=1800.0, active_calories=500.0)

    # Consumed 2300, burned 2300 = 0 balance
    # Target: 0, tolerance: 50
    assert record.is_deficit_on_track(0.0, tolerance_kcal=50.0) is True


def test_is_deficit_on_track_no_data(profile_id: ProfileId) -> None:
    """Test deficit tracking returns None if data incomplete."""
    record = ProgressRecord.create(
        profile_id=profile_id,
        date=date(2024, 1, 1),
        weight=80.0,
    )

    assert record.is_deficit_on_track(-500.0) is None
