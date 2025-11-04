"""Mutation resolvers for nutritional profile domain.

These resolvers execute CQRS commands using Command Handlers:
- createNutritionalProfile: Create new profile with BMR/TDEE/macros
- updateNutritionalProfile: Update user data or goal
- recordProgress: Track daily weight and consumption
"""

from datetime import date as date_type
from typing import TYPE_CHECKING
import strawberry

if TYPE_CHECKING:
    from domain.nutritional_profile.core.entities.profile import NutritionalProfile  # noqa: E501

from application.nutritional_profile.commands.create_profile import (
    CreateProfileCommand,
    CreateProfileHandler,
)
from application.nutritional_profile.commands.update_profile import (
    UpdateProfileCommand,
    UpdateProfileHandler,
)
from application.nutritional_profile.commands.record_progress import (
    RecordProgressCommand,
    RecordProgressHandler,
)
from graphql.types_nutritional_profile import (
    CreateProfileInput,
    UpdateProfileInput,
    RecordProgressInput,
    NutritionalProfileType,
    ProgressRecordType,
    BMRType,
    TDEEType,
    MacroSplitType,
    SexEnum,
    ActivityLevelEnum,
    GoalEnum,
    UserDataType,
)
from domain.nutritional_profile.core.value_objects.user_data import (
    UserData as DomainUserData,
)
from domain.nutritional_profile.core.value_objects.activity_level import (
    ActivityLevel,
)
from domain.nutritional_profile.core.value_objects.goal import Goal
from domain.nutritional_profile.core.value_objects.profile_id import ProfileId


# ============================================
# HELPER FUNCTIONS
# ============================================


def map_domain_user_data_to_graphql(user_data: DomainUserData) -> UserDataType:  # noqa: E501
    """Map domain UserData to GraphQL UserDataType."""
    # Map domain sex ('M'/'F') to GraphQL enum
    sex_enum = SexEnum.M if user_data.sex == "M" else SexEnum.F

    # Map domain activity level to GraphQL enum
    activity_map = {
        "sedentary": ActivityLevelEnum.SEDENTARY,
        "light": ActivityLevelEnum.LIGHT,
        "moderate": ActivityLevelEnum.MODERATE,
        "active": ActivityLevelEnum.ACTIVE,
        "very_active": ActivityLevelEnum.VERY_ACTIVE,
    }
    activity_enum = activity_map[user_data.activity_level.value]

    return UserDataType(
        weight=user_data.weight,
        height=user_data.height,
        age=user_data.age,
        sex=sex_enum,
        activity_level=activity_enum,
    )


def map_domain_profile_to_graphql(
    profile: "NutritionalProfile",
) -> NutritionalProfileType:
    """Map domain NutritionalProfile to GraphQL NutritionalProfileType."""
    # Map goal to GraphQL enum
    goal_map = {
        "cut": GoalEnum.CUT,
        "maintain": GoalEnum.MAINTAIN,
        "bulk": GoalEnum.BULK,
    }
    goal_enum = goal_map[profile.goal.value]

    # Map activity level to GraphQL enum for TDEE
    activity_map = {
        "sedentary": ActivityLevelEnum.SEDENTARY,
        "light": ActivityLevelEnum.LIGHT,
        "moderate": ActivityLevelEnum.MODERATE,
        "active": ActivityLevelEnum.ACTIVE,
        "very_active": ActivityLevelEnum.VERY_ACTIVE,
    }
    activity_enum = activity_map[profile.user_data.activity_level.value]

    return NutritionalProfileType(
        profile_id=str(profile.profile_id),
        user_id=profile.user_id,
        user_data=map_domain_user_data_to_graphql(profile.user_data),
        goal=goal_enum,
        bmr=BMRType(value=profile.bmr.value),
        tdee=TDEEType(
            value=profile.tdee.value,
            activity_level=activity_enum,
        ),
        calories_target=profile.calories_target,
        macro_split=MacroSplitType(
            protein_g=profile.macro_split.protein_g,
            carbs_g=profile.macro_split.carbs_g,
            fat_g=profile.macro_split.fat_g,
        ),
        progress_history=[
            ProgressRecordType(
                date=record.date,
                weight=record.weight,
                consumed_calories=record.consumed_calories,
                consumed_protein_g=record.consumed_protein_g,
                consumed_carbs_g=record.consumed_carbs_g,
                consumed_fat_g=record.consumed_fat_g,
                calories_burned_bmr=record.calories_burned_bmr,
                calories_burned_active=record.calories_burned_active,
                notes=record.notes,
            )
            for record in profile.progress_history
        ],
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


# ============================================
# MUTATION RESOLVERS
# ============================================


@strawberry.type
class NutritionalProfileMutations:
    """Mutations for nutritional profile operations."""

    @strawberry.mutation
    async def create_nutritional_profile(
        self, info: strawberry.types.Info, input: CreateProfileInput
    ) -> NutritionalProfileType:
        """Create new nutritional profile with personalized calculations.

        Workflow:
        1. Calculate BMR using Mifflin-St Jeor formula
        2. Calculate TDEE (BMR × activity level multiplier)
        3. Adjust calories for goal (cut/maintain/bulk)
        4. Calculate macronutrient distribution
        5. Create profile with initial progress record
        6. Publish ProfileCreated event
        7. Store in repository

        Args:
            info: Strawberry field info (injected)
            input: CreateProfileInput with user data and goal

        Returns:
            NutritionalProfileType with all calculations

        Example:
            mutation {
              createNutritionalProfile(input: {
                userId: "user123"
                userData: {
                  weight: 70.0
                  height: 175.0
                  age: 30
                  sex: "M"
                  activityLevel: "moderate"
                }
                goal: "cut"
                initialWeight: 70.0
              }) {
                profileId
                bmr { value }
                tdee { value }
                caloriesTarget
                macroSplit { proteinG, carbsG, fatG }
              }
            }
        """
        context = info.context
        orchestrator = context.get("profile_orchestrator")
        repository = context.get("profile_repository")
        event_bus = context.get("event_bus")

        if not all([orchestrator, repository, event_bus]):
            raise Exception("Missing dependencies in GraphQL context")

        # Get factory
        from domain.nutritional_profile.core.factories.profile_factory import (
            NutritionalProfileFactory,
        )  # noqa: E501

        factory = NutritionalProfileFactory()

        # Map GraphQL input to domain types
        # Convert GraphQL enum to string for domain
        sex_str = input.user_data.sex.value
        activity_str = input.user_data.activity_level.value
        goal_str = input.goal.value

        user_data = DomainUserData(
            weight=input.user_data.weight,
            height=input.user_data.height,
            age=input.user_data.age,
            sex=sex_str,  # type: ignore
            activity_level=ActivityLevel(activity_str),
        )
        goal = Goal(goal_str)
        initial_date = input.initial_date or date_type.today()

        # Create command
        command = CreateProfileCommand(
            user_id=input.user_id,
            user_data=user_data,
            goal=goal,
            initial_weight=input.initial_weight,
            initial_date=initial_date,
        )

        # Execute via handler
        handler = CreateProfileHandler(
            orchestrator=orchestrator,
            repository=repository,
            factory=factory,
        )

        result = await handler.handle(command)

        # Map to GraphQL type (extract profile from result)
        return map_domain_profile_to_graphql(result.profile)

    @strawberry.mutation
    async def update_nutritional_profile(
        self, info: strawberry.types.Info, input: UpdateProfileInput
    ) -> NutritionalProfileType:
        """Update nutritional profile (user data or goal change).

        Recalculates BMR/TDEE/macros if user data changes.

        Args:
            info: Strawberry field info (injected)
            input: UpdateProfileInput with optional user_data or goal

        Returns:
            Updated NutritionalProfileType

        Example:
            mutation {
              updateNutritionalProfile(input: {
                profileId: "abc123"
                goal: "maintain"
              }) {
                profileId
                goal
                caloriesTarget
              }
            }
        """
        context = info.context
        orchestrator = context.get("profile_orchestrator")
        repository = context.get("profile_repository")
        event_bus = context.get("event_bus")

        if not all([orchestrator, repository, event_bus]):
            raise Exception("Missing dependencies in GraphQL context")

        # Map GraphQL input to domain types
        user_data = None
        if input.user_data:
            # Convert GraphQL enum to string for domain
            sex_str = input.user_data.sex.value
            activity_str = input.user_data.activity_level.value

            user_data = DomainUserData(
                weight=input.user_data.weight,
                height=input.user_data.height,
                age=input.user_data.age,
                sex=sex_str,  # type: ignore
                activity_level=ActivityLevel(activity_str),
            )

        goal = Goal(input.goal.value) if input.goal else None

        # Create command
        command = UpdateProfileCommand(
            profile_id=ProfileId.from_string(input.profile_id),
            user_data=user_data,
            goal=goal,
        )

        # Execute via handler
        handler = UpdateProfileHandler(
            orchestrator=orchestrator,
            repository=repository,
        )

        result = await handler.handle(command)

        # Map to GraphQL type (extract profile from result)
        return map_domain_profile_to_graphql(result.profile)

    @strawberry.mutation
    async def record_progress(
        self, info: strawberry.types.Info, input: RecordProgressInput
    ) -> ProgressRecordType:
        """Record daily progress (weight, calories, macros).

        Args:
            info: Strawberry field info (injected)
            input: RecordProgressInput with date, weight, consumption

        Returns:
            ProgressRecordType for the recorded day

        Example:
            mutation {
              recordProgress(input: {
                profileId: "abc123"
                date: "2025-10-31"
                weight: 69.5
                consumedCalories: 1800
                consumedProteinG: 140
                consumedCarbsG: 180
                consumedFatG: 60
                caloriesBurnedBmr: 1680
                caloriesBurnedActive: 420
              }) {
                date
                weight
                calorieBalance
              }
            }
        """
        context = info.context
        repository = context.get("profile_repository")
        event_bus = context.get("event_bus")

        if not all([repository, event_bus]):
            raise Exception("Missing dependencies in GraphQL context")

        # Create command
        command = RecordProgressCommand(
            profile_id=ProfileId.from_string(input.profile_id),
            measurement_date=input.date,
            weight=input.weight,
            consumed_calories=input.consumed_calories,
            consumed_protein_g=input.consumed_protein_g,
            consumed_carbs_g=input.consumed_carbs_g,
            consumed_fat_g=input.consumed_fat_g,
            calories_burned_bmr=input.calories_burned_bmr,
            calories_burned_active=input.calories_burned_active,
            notes=input.notes,
        )

        # Execute via handler
        handler = RecordProgressHandler(
            repository=repository,
        )

        result = await handler.handle(command)
        record = result.progress_record

        # Map to GraphQL type
        return ProgressRecordType(
            date=record.date,
            weight=record.weight,
            consumed_calories=record.consumed_calories,
            consumed_protein_g=record.consumed_protein_g,
            consumed_carbs_g=record.consumed_carbs_g,
            consumed_fat_g=record.consumed_fat_g,
            calories_burned_bmr=record.calories_burned_bmr,
            calories_burned_active=record.calories_burned_active,
            notes=record.notes,
        )
