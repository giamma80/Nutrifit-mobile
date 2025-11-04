"""CreateProfileCommand - create a new nutritional profile."""

from dataclasses import dataclass
from datetime import date as DateType
from typing import Optional

from domain.nutritional_profile.core.entities.nutritional_profile import (
    NutritionalProfile,
)
from domain.nutritional_profile.core.entities.progress_record import (
    ProgressRecord,
)
from domain.nutritional_profile.core.factories.profile_factory import (
    NutritionalProfileFactory,
)
from domain.nutritional_profile.core.ports.repository import (
    IProfileRepository,
)
from domain.nutritional_profile.core.value_objects.goal import Goal
from domain.nutritional_profile.core.value_objects.user_data import UserData

from ..orchestrators.profile_orchestrator import ProfileOrchestrator


@dataclass(frozen=True)
class CreateProfileCommand:
    """Command to create a new nutritional profile.

    Attributes:
        user_id: User identifier (from authentication)
        user_data: User biometric data with activity level
        goal: Nutritional goal (cut/maintain/bulk)
        initial_weight: Initial weight for progress tracking
        initial_date: Date of initial measurement (defaults to today)
    """

    user_id: str
    user_data: UserData
    goal: Goal
    initial_weight: float
    initial_date: Optional[DateType] = None


@dataclass(frozen=True)
class CreateProfileResult:
    """Result of profile creation.

    Attributes:
        profile: Created nutritional profile
        initial_progress: Initial progress record
    """

    profile: NutritionalProfile
    initial_progress: ProgressRecord


class CreateProfileHandler:
    """Handler for CreateProfileCommand.

    Creates a new nutritional profile by:
    1. Calculating BMR, TDEE, and macro targets via orchestrator
    2. Creating profile entity via factory
    3. Persisting profile to repository
    """

    def __init__(
        self,
        orchestrator: ProfileOrchestrator,
        repository: IProfileRepository,
        factory: NutritionalProfileFactory,
    ):
        self._orchestrator = orchestrator
        self._repository = repository
        self._factory = factory

    async def handle(self, command: CreateProfileCommand) -> CreateProfileResult:
        """
        Handle profile creation command.

        Args:
            command: CreateProfileCommand with user data and goal

        Returns:
            CreateProfileResult with created profile and progress

        Raises:
            InvalidUserDataError: If user data validation fails
            ProfileDomainError: If profile creation fails
        """
        # Step 1: Calculate all nutritional metrics
        calculations = self._orchestrator.calculate_profile_metrics(
            user_data=command.user_data,
            goal=command.goal,
        )

        # Step 2: Create profile entity with initial progress
        profile = self._factory.create(
            user_id=command.user_id,
            user_data=command.user_data,
            goal=command.goal,
            bmr=calculations.bmr,
            tdee=calculations.tdee,
            calories_target=calculations.calories_target,
            macro_split=calculations.macro_split,
            initial_weight=command.initial_weight,
            initial_date=command.initial_date or DateType.today(),  # Default to today
        )

        # Step 3: Persist profile
        await self._repository.save(profile)

        # Get initial progress record for response
        initial_progress = profile.progress_history[0]

        return CreateProfileResult(profile=profile, initial_progress=initial_progress)
