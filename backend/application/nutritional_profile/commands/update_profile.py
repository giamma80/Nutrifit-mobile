"""UpdateProfileCommand - update an existing nutritional profile."""

from dataclasses import dataclass
from typing import Optional

from domain.nutritional_profile.core.entities.nutritional_profile import (
    NutritionalProfile,
)
from domain.nutritional_profile.core.ports.repository import (
    IProfileRepository,
)
from domain.nutritional_profile.core.value_objects.goal import Goal
from domain.nutritional_profile.core.value_objects.profile_id import ProfileId
from domain.nutritional_profile.core.value_objects.user_data import UserData

from ..orchestrators.profile_orchestrator import ProfileOrchestrator


@dataclass(frozen=True)
class UpdateProfileCommand:
    """Command to update an existing nutritional profile.

    Attributes:
        profile_id: Profile to update
        user_data: Optional updated user data
        goal: Optional updated goal

    Note: At least one field (user_data or goal) must be provided.
    """

    profile_id: ProfileId
    user_data: Optional[UserData] = None
    goal: Optional[Goal] = None

    def __post_init__(self) -> None:
        """Validate command has at least one update."""
        if self.user_data is None and self.goal is None:
            raise ValueError("At least one field must be provided for update")


@dataclass(frozen=True)
class UpdateProfileResult:
    """Result of profile update.

    Attributes:
        profile: Updated nutritional profile
        recalculated: Whether metrics were recalculated
    """

    profile: NutritionalProfile
    recalculated: bool


class UpdateProfileHandler:
    """Handler for UpdateProfileCommand.

    Updates an existing profile by:
    1. Loading profile from repository
    2. Applying updates (user_data and/or goal)
    3. Recalculating metrics if needed
    4. Persisting updated profile
    """

    def __init__(
        self,
        orchestrator: ProfileOrchestrator,
        repository: IProfileRepository,
    ):
        self._orchestrator = orchestrator
        self._repository = repository

    async def handle(self, command: UpdateProfileCommand) -> UpdateProfileResult:
        """
        Handle profile update command.

        Args:
            command: UpdateProfileCommand with profile ID and updates

        Returns:
            UpdateProfileResult with updated profile

        Raises:
            ProfileNotFoundError: If profile doesn't exist
            InvalidUserDataError: If user data validation fails
        """
        # Step 1: Load existing profile
        profile = await self._repository.find_by_id(command.profile_id)
        if profile is None:
            from domain.nutritional_profile.core.exceptions.domain_errors import (  # noqa: E501
                ProfileNotFoundError,
            )

            raise ProfileNotFoundError(f"Profile {command.profile_id} not found")

        # Step 2: Determine what needs updating
        updated_user_data = command.user_data or profile.user_data
        updated_goal = command.goal or profile.goal

        # Check if recalculation is needed
        needs_recalc = command.user_data is not None or command.goal is not None

        # Step 3: Recalculate if needed
        if needs_recalc:
            # Update user data if provided
            if command.user_data is not None:
                profile.update_user_data(
                    weight=command.user_data.weight,
                    height=command.user_data.height,
                    age=command.user_data.age,
                    activity_level=command.user_data.activity_level.value,
                )

            # Update goal if provided
            if command.goal is not None:
                profile.update_goal(command.goal)

            # Recalculate metrics with updated data
            calculations = self._orchestrator.recalculate_metrics(
                user_data=updated_user_data,
                goal=updated_goal,
            )

            # Update profile calculations
            profile.update_calculations(
                bmr=calculations.bmr,
                tdee=calculations.tdee,
                calories_target=calculations.calories_target,
                macro_split=calculations.macro_split,
            )

        # Step 4: Persist updated profile
        await self._repository.save(profile)

        return UpdateProfileResult(profile=profile, recalculated=needs_recalc)
