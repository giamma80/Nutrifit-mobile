"""Unit tests for ProgressRecord macro tracking."""

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


def test_update_consumed_macros(profile_id: ProfileId) -> None:
    """Test updating consumed macros."""
    record = ProgressRecord.create(
        profile_id=profile_id,
        date=date(2024, 1, 1),
        weight=80.0,
    )

    record.update_consumed_macros(protein_g=176.0, carbs_g=248.0, fat_g=63.0)

    assert record.consumed_protein_g == 176.0
    assert record.consumed_carbs_g == 248.0
    assert record.consumed_fat_g == 63.0
    # Auto-calculated calories: 176*4 + 248*4 + 63*9 = 2263 kcal
    assert record.consumed_calories == 2263.0


def test_update_consumed_macros_validation(profile_id: ProfileId) -> None:
    """Test macro validation."""
    record = ProgressRecord.create(
        profile_id=profile_id,
        date=date(2024, 1, 1),
        weight=80.0,
    )

    with pytest.raises(ValueError, match="Protein must be non-negative"):
        record.update_consumed_macros(protein_g=-10.0, carbs_g=200.0, fat_g=50.0)

    with pytest.raises(ValueError, match="Carbs must be non-negative"):
        record.update_consumed_macros(protein_g=150.0, carbs_g=-50.0, fat_g=50.0)

    with pytest.raises(ValueError, match="Fat must be non-negative"):
        record.update_consumed_macros(protein_g=150.0, carbs_g=200.0, fat_g=-20.0)


def test_macro_protein_delta(profile_id: ProfileId) -> None:
    """Test protein delta calculation."""
    record = ProgressRecord.create(
        profile_id=profile_id,
        date=date(2024, 1, 1),
        weight=80.0,
    )

    record.update_consumed_macros(protein_g=180.0, carbs_g=250.0, fat_g=65.0)

    # Target: 176g, Consumed: 180g, Delta: +4g
    assert record.macro_protein_delta(176.0) == 4.0


def test_macro_carbs_delta(profile_id: ProfileId) -> None:
    """Test carbs delta calculation."""
    record = ProgressRecord.create(
        profile_id=profile_id,
        date=date(2024, 1, 1),
        weight=80.0,
    )

    record.update_consumed_macros(protein_g=176.0, carbs_g=240.0, fat_g=63.0)

    # Target: 248g, Consumed: 240g, Delta: -8g
    assert record.macro_carbs_delta(248.0) == -8.0


def test_macro_fat_delta(profile_id: ProfileId) -> None:
    """Test fat delta calculation."""
    record = ProgressRecord.create(
        profile_id=profile_id,
        date=date(2024, 1, 1),
        weight=80.0,
    )

    record.update_consumed_macros(protein_g=176.0, carbs_g=248.0, fat_g=70.0)

    # Target: 63g, Consumed: 70g, Delta: +7g
    assert record.macro_fat_delta(63.0) == 7.0


def test_macro_deltas_no_data(profile_id: ProfileId) -> None:
    """Test macro deltas return None when no data."""
    record = ProgressRecord.create(
        profile_id=profile_id,
        date=date(2024, 1, 1),
        weight=80.0,
    )

    assert record.macro_protein_delta(176.0) is None
    assert record.macro_carbs_delta(248.0) is None
    assert record.macro_fat_delta(63.0) is None


def test_are_macros_on_track_all_within_tolerance(
    profile_id: ProfileId,
) -> None:
    """Test macros on track when all within tolerance."""
    record = ProgressRecord.create(
        profile_id=profile_id,
        date=date(2024, 1, 1),
        weight=80.0,
    )

    # Within 10g tolerance for all macros
    record.update_consumed_macros(protein_g=178.0, carbs_g=245.0, fat_g=65.0)

    assert (
        record.are_macros_on_track(
            target_protein_g=176.0,
            target_carbs_g=248.0,
            target_fat_g=63.0,
            tolerance_grams=10.0,
        )
        is True
    )


def test_are_macros_on_track_protein_outside_tolerance(
    profile_id: ProfileId,
) -> None:
    """Test macros off track when protein outside tolerance."""
    record = ProgressRecord.create(
        profile_id=profile_id,
        date=date(2024, 1, 1),
        weight=80.0,
    )

    # Protein off by 15g (outside 10g tolerance)
    record.update_consumed_macros(protein_g=191.0, carbs_g=248.0, fat_g=63.0)

    assert (
        record.are_macros_on_track(
            target_protein_g=176.0,
            target_carbs_g=248.0,
            target_fat_g=63.0,
            tolerance_grams=10.0,
        )
        is False
    )


def test_are_macros_on_track_carbs_outside_tolerance(
    profile_id: ProfileId,
) -> None:
    """Test macros off track when carbs outside tolerance."""
    record = ProgressRecord.create(
        profile_id=profile_id,
        date=date(2024, 1, 1),
        weight=80.0,
    )

    # Carbs off by 20g (outside 10g tolerance)
    record.update_consumed_macros(protein_g=176.0, carbs_g=268.0, fat_g=63.0)

    assert (
        record.are_macros_on_track(
            target_protein_g=176.0,
            target_carbs_g=248.0,
            target_fat_g=63.0,
            tolerance_grams=10.0,
        )
        is False
    )


def test_are_macros_on_track_fat_outside_tolerance(
    profile_id: ProfileId,
) -> None:
    """Test macros off track when fat outside tolerance."""
    record = ProgressRecord.create(
        profile_id=profile_id,
        date=date(2024, 1, 1),
        weight=80.0,
    )

    # Fat off by 12g (outside 10g tolerance)
    record.update_consumed_macros(protein_g=176.0, carbs_g=248.0, fat_g=75.0)

    assert (
        record.are_macros_on_track(
            target_protein_g=176.0,
            target_carbs_g=248.0,
            target_fat_g=63.0,
            tolerance_grams=10.0,
        )
        is False
    )


def test_are_macros_on_track_no_data(profile_id: ProfileId) -> None:
    """Test macros on track returns None when no data."""
    record = ProgressRecord.create(
        profile_id=profile_id,
        date=date(2024, 1, 1),
        weight=80.0,
    )

    assert (
        record.are_macros_on_track(
            target_protein_g=176.0,
            target_carbs_g=248.0,
            target_fat_g=63.0,
        )
        is None
    )


def test_are_macros_on_track_exact_match(profile_id: ProfileId) -> None:
    """Test macros on track with exact match."""
    record = ProgressRecord.create(
        profile_id=profile_id,
        date=date(2024, 1, 1),
        weight=80.0,
    )

    # Exact match
    record.update_consumed_macros(protein_g=176.0, carbs_g=248.0, fat_g=63.0)

    assert (
        record.are_macros_on_track(
            target_protein_g=176.0,
            target_carbs_g=248.0,
            target_fat_g=63.0,
            tolerance_grams=0.0,
        )
        is True
    )


def test_are_macros_on_track_custom_tolerance(profile_id: ProfileId) -> None:
    """Test macros on track with custom tolerance."""
    record = ProgressRecord.create(
        profile_id=profile_id,
        date=date(2024, 1, 1),
        weight=80.0,
    )

    # 15g off on each macro
    record.update_consumed_macros(protein_g=191.0, carbs_g=263.0, fat_g=78.0)

    # Should be off track with 10g tolerance
    assert (
        record.are_macros_on_track(
            target_protein_g=176.0,
            target_carbs_g=248.0,
            target_fat_g=63.0,
            tolerance_grams=10.0,
        )
        is False
    )

    # Should be on track with 20g tolerance
    assert (
        record.are_macros_on_track(
            target_protein_g=176.0,
            target_carbs_g=248.0,
            target_fat_g=63.0,
            tolerance_grams=20.0,
        )
        is True
    )
