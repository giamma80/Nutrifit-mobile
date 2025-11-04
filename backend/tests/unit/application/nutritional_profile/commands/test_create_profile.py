"""Unit tests for CreateProfileCommand and handler."""

from datetime import date
from unittest.mock import AsyncMock, Mock

import pytest

from application.nutritional_profile.commands.create_profile import (
    CreateProfileCommand,
    CreateProfileHandler,
    CreateProfileResult,
)
from application.nutritional_profile.orchestrators.profile_orchestrator import (  # noqa: E501
    ProfileCalculations,
    ProfileOrchestrator,
)
from domain.nutritional_profile.core.entities.nutritional_profile import (
    NutritionalProfile,
)
from domain.nutritional_profile.core.factories.profile_factory import (
    NutritionalProfileFactory,
)
from domain.nutritional_profile.core.value_objects.activity_level import (
    ActivityLevel,
)
from domain.nutritional_profile.core.value_objects.bmr import BMR
from domain.nutritional_profile.core.value_objects.goal import Goal
from domain.nutritional_profile.core.value_objects.macro_split import (
    MacroSplit,
)
from domain.nutritional_profile.core.value_objects.tdee import TDEE
from domain.nutritional_profile.core.value_objects.user_data import UserData


@pytest.fixture
def mock_orchestrator() -> Mock:
    """Create mock orchestrator."""
    orchestrator = Mock(spec=ProfileOrchestrator)
    orchestrator.calculate_profile_metrics.return_value = ProfileCalculations(
        bmr=BMR(value=1780.0),
        tdee=TDEE(value=2759.0),
        calories_target=2259.0,
        macro_split=MacroSplit(protein_g=176, carbs_g=248, fat_g=63),
    )
    return orchestrator


@pytest.fixture
def mock_repository() -> AsyncMock:
    """Create mock repository."""
    repository = AsyncMock()
    return repository


@pytest.fixture
def handler(
    mock_orchestrator: Mock,
    mock_repository: AsyncMock,
) -> CreateProfileHandler:
    """Create handler with mocks."""
    return CreateProfileHandler(
        orchestrator=mock_orchestrator,
        repository=mock_repository,
        factory=NutritionalProfileFactory(),
    )


@pytest.fixture
def sample_command() -> CreateProfileCommand:
    """Create sample command."""
    return CreateProfileCommand(
        user_id="user123",
        user_data=UserData(
            weight=80.0,
            height=180.0,
            age=30,
            sex="M",
            activity_level=ActivityLevel.MODERATE,
        ),
        goal=Goal.CUT,
        initial_weight=80.0,
        initial_date=date(2024, 1, 1),
    )


@pytest.mark.asyncio
async def test_create_profile_success(
    handler: CreateProfileHandler,
    sample_command: CreateProfileCommand,
    mock_orchestrator: Mock,
    mock_repository: AsyncMock,
) -> None:
    """Test successful profile creation."""
    result = await handler.handle(sample_command)

    # Verify result structure
    assert isinstance(result, CreateProfileResult)
    assert isinstance(result.profile, NutritionalProfile)
    assert result.profile.user_id == "user123"
    assert result.profile.goal == Goal.CUT

    # Verify orchestrator was called
    mock_orchestrator.calculate_profile_metrics.assert_called_once()
    call_args = mock_orchestrator.calculate_profile_metrics.call_args
    assert call_args.kwargs["user_data"].weight == 80.0
    assert call_args.kwargs["goal"] == Goal.CUT

    # Verify repository save was called
    mock_repository.save.assert_called_once()
    saved_profile = mock_repository.save.call_args[0][0]
    assert isinstance(saved_profile, NutritionalProfile)


@pytest.mark.asyncio
async def test_create_profile_with_initial_progress(
    handler: CreateProfileHandler,
    sample_command: CreateProfileCommand,
) -> None:
    """Test profile created with initial progress record."""
    result = await handler.handle(sample_command)

    # Profile should have initial progress
    assert len(result.profile.progress_history) == 1
    assert result.initial_progress.weight == 80.0
    assert result.initial_progress.date == date(2024, 1, 1)


@pytest.mark.asyncio
async def test_create_profile_default_date(
    handler: CreateProfileHandler,
    mock_repository: AsyncMock,
) -> None:
    """Test profile creation with default date (today)."""
    command = CreateProfileCommand(
        user_id="user123",
        user_data=UserData(
            weight=80.0,
            height=180.0,
            age=30,
            sex="M",
            activity_level=ActivityLevel.MODERATE,
        ),
        goal=Goal.CUT,
        initial_weight=80.0,
        # initial_date not provided - should default to today
    )

    result = await handler.handle(command)

    # Should use today's date
    assert result.initial_progress.date == date.today()


@pytest.mark.asyncio
async def test_create_profile_different_goals(
    handler: CreateProfileHandler,
) -> None:
    """Test profile creation with different goals."""
    goals = [Goal.CUT, Goal.MAINTAIN, Goal.BULK]

    for goal in goals:
        command = CreateProfileCommand(
            user_id=f"user_{goal.value}",
            user_data=UserData(
                weight=80.0,
                height=180.0,
                age=30,
                sex="M",
                activity_level=ActivityLevel.MODERATE,
            ),
            goal=goal,
            initial_weight=80.0,
        )

        result = await handler.handle(command)
        assert result.profile.goal == goal


@pytest.mark.asyncio
async def test_create_profile_invalid_user_data(
    handler: CreateProfileHandler,
) -> None:
    """Test profile creation with invalid user data."""
    with pytest.raises(Exception):  # Will raise InvalidUserDataError
        command = CreateProfileCommand(
            user_id="user123",
            user_data=UserData(
                weight=-10.0,  # Invalid weight
                height=180.0,
                age=30,
                sex="M",
                activity_level=ActivityLevel.MODERATE,
            ),
            goal=Goal.CUT,
            initial_weight=80.0,
        )
        await handler.handle(command)


@pytest.mark.asyncio
async def test_create_profile_profile_id_generated(
    handler: CreateProfileHandler,
    sample_command: CreateProfileCommand,
) -> None:
    """Test profile ID is generated."""
    result = await handler.handle(sample_command)

    # Profile should have valid UUID
    assert result.profile.profile_id is not None
    assert str(result.profile.profile_id)  # Should convert to string


@pytest.mark.asyncio
async def test_create_profile_calculations_stored(
    handler: CreateProfileHandler,
    sample_command: CreateProfileCommand,
) -> None:
    """Test calculations are stored in profile."""
    result = await handler.handle(sample_command)

    # Verify calculations from mock
    assert result.profile.bmr.value == 1780.0
    assert result.profile.tdee.value == 2759.0
    assert result.profile.calories_target == 2259.0
    assert result.profile.macro_split.protein_g == 176
