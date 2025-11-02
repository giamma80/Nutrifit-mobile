"""Unit tests for ProfileOrchestrator."""

import pytest

from application.nutritional_profile.orchestrators.profile_orchestrator import (  # noqa: E501
    ProfileCalculations,
    ProfileOrchestrator,
)
from domain.nutritional_profile.calculation.bmr_service import BMRService
from domain.nutritional_profile.calculation.macro_service import MacroService
from domain.nutritional_profile.calculation.tdee_service import TDEEService
from domain.nutritional_profile.core.value_objects.activity_level import (
    ActivityLevel,
)
from domain.nutritional_profile.core.value_objects.goal import Goal
from domain.nutritional_profile.core.value_objects.user_data import UserData


@pytest.fixture
def orchestrator() -> ProfileOrchestrator:
    """Create orchestrator with real services."""
    return ProfileOrchestrator(
        bmr_service=BMRService(),
        tdee_service=TDEEService(),
        macro_service=MacroService(),
    )


@pytest.fixture
def sample_user_data() -> UserData:
    """Create sample user data."""
    return UserData(
        weight=80.0,
        height=180.0,
        age=30,
        sex="M",
        activity_level=ActivityLevel.MODERATE,
    )


def test_calculate_profile_metrics_cut(
    orchestrator: ProfileOrchestrator, sample_user_data: UserData
) -> None:
    """Test profile calculation for CUT goal."""
    result = orchestrator.calculate_profile_metrics(
        user_data=sample_user_data,
        goal=Goal.CUT,
    )

    assert isinstance(result, ProfileCalculations)
    assert result.bmr.value == 1780.0  # 80kg male, 30y, 180cm
    assert result.tdee.value == 2759.0  # BMR × 1.55 (moderate)
    assert result.calories_target == 2259.0  # TDEE - 500 (cut)
    assert result.macro_split.protein_g == 176  # 80 × 2.2
    assert result.macro_split.fat_g == 63  # 2259 × 0.25 / 9
    assert result.macro_split.carbs_g == 248  # remainder


def test_calculate_profile_metrics_maintain(
    orchestrator: ProfileOrchestrator, sample_user_data: UserData
) -> None:
    """Test profile calculation for MAINTAIN goal."""
    result = orchestrator.calculate_profile_metrics(
        user_data=sample_user_data,
        goal=Goal.MAINTAIN,
    )

    assert result.bmr.value == 1780.0
    assert result.tdee.value == 2759.0
    assert result.calories_target == 2759.0  # No adjustment
    assert result.macro_split.protein_g == 144  # 80 × 1.8
    assert result.macro_split.fat_g == 92  # 2759 × 0.30 / 9


def test_calculate_profile_metrics_bulk(
    orchestrator: ProfileOrchestrator, sample_user_data: UserData
) -> None:
    """Test profile calculation for BULK goal."""
    result = orchestrator.calculate_profile_metrics(
        user_data=sample_user_data,
        goal=Goal.BULK,
    )

    assert result.bmr.value == 1780.0
    assert result.tdee.value == 2759.0
    assert result.calories_target == 3059.0  # TDEE + 300 (bulk)
    assert result.macro_split.protein_g == 160  # 80 × 2.0
    assert result.macro_split.fat_g == 68  # 3059 × 0.20 / 9


def test_calculate_profile_metrics_different_activity_levels(
    orchestrator: ProfileOrchestrator,
) -> None:
    """Test calculation with different activity levels."""
    user_sedentary = UserData(
        weight=80.0,
        height=180.0,
        age=30,
        sex="M",
        activity_level=ActivityLevel.SEDENTARY,
    )

    result_sedentary = orchestrator.calculate_profile_metrics(
        user_data=user_sedentary,
        goal=Goal.MAINTAIN,
    )

    user_active = UserData(
        weight=80.0,
        height=180.0,
        age=30,
        sex="M",
        activity_level=ActivityLevel.VERY_ACTIVE,
    )

    result_active = orchestrator.calculate_profile_metrics(
        user_data=user_active,
        goal=Goal.MAINTAIN,
    )

    # TDEE should increase with activity level
    assert result_sedentary.tdee.value < result_active.tdee.value
    assert result_sedentary.calories_target < result_active.calories_target


def test_calculate_profile_metrics_female(orchestrator: ProfileOrchestrator) -> None:
    """Test calculation for female user."""
    user_female = UserData(
        weight=60.0,
        height=165.0,
        age=25,
        sex="F",
        activity_level=ActivityLevel.MODERATE,
    )

    result = orchestrator.calculate_profile_metrics(
        user_data=user_female,
        goal=Goal.CUT,
    )

    # Female BMR: 10*60 + 6.25*165 - 5*25 - 161 = 1345.25
    assert result.bmr.value == 1345.25
    assert result.tdee.value == pytest.approx(2085.14, rel=0.01)
    assert result.calories_target == pytest.approx(1585.14, rel=0.01)


def test_recalculate_metrics_same_as_calculate(
    orchestrator: ProfileOrchestrator, sample_user_data: UserData
) -> None:
    """Test recalculate_metrics produces same result."""
    result1 = orchestrator.calculate_profile_metrics(
        user_data=sample_user_data,
        goal=Goal.CUT,
    )

    result2 = orchestrator.recalculate_metrics(
        user_data=sample_user_data,
        goal=Goal.CUT,
    )

    assert result1.bmr.value == result2.bmr.value
    assert result1.tdee.value == result2.tdee.value
    assert result1.calories_target == result2.calories_target
    assert result1.macro_split.protein_g == result2.macro_split.protein_g


def test_orchestrator_immutability(
    orchestrator: ProfileOrchestrator, sample_user_data: UserData
) -> None:
    """Test orchestrator doesn't mutate input data."""
    original_weight = sample_user_data.weight

    orchestrator.calculate_profile_metrics(
        user_data=sample_user_data,
        goal=Goal.CUT,
    )

    assert sample_user_data.weight == original_weight


def test_orchestrator_with_extreme_values(orchestrator: ProfileOrchestrator) -> None:
    """Test calculation with extreme but valid values."""
    user_extreme = UserData(
        weight=120.0,  # High weight
        height=200.0,  # Tall
        age=50,  # Older
        sex="M",
        activity_level=ActivityLevel.VERY_ACTIVE,
    )

    result = orchestrator.calculate_profile_metrics(
        user_data=user_extreme,
        goal=Goal.BULK,
    )

    # Should handle extreme values without error
    assert result.bmr.value > 0
    assert result.tdee.value > result.bmr.value
    assert result.calories_target > 0
    assert result.macro_split.total_calories() > 0
