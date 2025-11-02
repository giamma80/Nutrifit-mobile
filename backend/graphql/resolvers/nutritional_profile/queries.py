"""Query resolvers for nutritional profile domain.

These resolvers retrieve profile data and statistics:
- nutritionalProfile: Get profile by ID or user ID
- progressScore: Calculate progress statistics over date range
"""

from datetime import date as date_type
from typing import Optional, TYPE_CHECKING
import strawberry

from graphql.types_nutritional_profile import (
    NutritionalProfileType,
    ProgressStatisticsType,
    BMRType,
    TDEEType,
    MacroSplitType,
    UserDataType,
    ProgressRecordType,
    SexEnum,
    ActivityLevelEnum,
    GoalEnum,
)
from domain.nutritional_profile.core.value_objects.profile_id import ProfileId

if TYPE_CHECKING:
    from domain.nutritional_profile.core.entities.nutritional_profile import (  # noqa: E501
        NutritionalProfile,
    )
    from domain.nutritional_profile.core.value_objects.user_data import (
        UserData,
    )


# ============================================
# HELPER FUNCTIONS
# ============================================


def map_domain_user_data_to_graphql(user_data: "UserData") -> UserDataType:  # noqa: E501
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

    # Map activity level to GraphQL enum
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
# QUERY RESOLVERS
# ============================================


@strawberry.type
class NutritionalProfileQueries:
    """GraphQL queries for nutritional profile domain."""

    @strawberry.field
    async def nutritional_profile(
        self,
        info: strawberry.types.Info,
        profile_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Optional[NutritionalProfileType]:
        """Get nutritional profile by ID or user ID.

        Args:
            info: Strawberry field info (injected)
            profile_id: Optional profile ID
            user_id: Optional user ID

        Returns:
            NutritionalProfileType or None if not found

        Raises:
            Exception: If neither profile_id nor user_id provided

        Example:
            query {
              nutritionalProfile(userId: "user123") {
                profileId
                userId
                goal
                caloriesTarget
                macroSplit {
                  proteinG
                  carbsG
                  fatG
                }
                progressHistory {
                  date
                  weight
                  consumedCalories
                }
              }
            }
        """
        context = info.context
        repository = context.get("profile_repository")

        if not repository:
            raise Exception("Missing profile_repository in GraphQL context")

        if not profile_id and not user_id:
            raise Exception("Must provide either profile_id or user_id")

        # Query by ID or user ID
        profile = None
        if profile_id:
            profile = await repository.find_by_id(ProfileId.from_string(profile_id))
        elif user_id:
            profile = await repository.find_by_user_id(user_id)

        if profile:
            return map_domain_profile_to_graphql(profile)
        return None

    @strawberry.field
    async def progress_score(
        self,
        info: strawberry.types.Info,
        user_id: str,
        start_date: date_type,
        end_date: date_type,
    ) -> Optional[ProgressStatisticsType]:
        """Calculate progress statistics over date range.

        Args:
            info: Strawberry field info (injected)
            user_id: User ID to find profile
            start_date: Start date for statistics
            end_date: End date for statistics

        Returns:
            ProgressStatisticsType with aggregated stats

        Raises:
            Exception: If profile not found

        Example:
            query {
              progressScore(
                userId: "user123"
                startDate: "2024-01-01"
                endDate: "2024-01-31"
              ) {
                startDate
                endDate
                weightDelta
                avgDailyCalories
                totalDays
                adherenceRate
              }
            }
        """
        context = info.context
        repository = context.get("profile_repository")

        if not repository:
            raise Exception("Missing profile_repository in GraphQL context")

        # Get profile by user ID
        profile = await repository.find_by_user_id(user_id)

        if not profile:
            raise Exception(f"Profile for user {user_id} not found")

        # Calculate statistics using existing domain methods
        records = profile.get_progress_range(start_date, end_date)
        weight_delta = profile.calculate_weight_delta(start_date, end_date)
        avg_calories = profile.average_daily_calories(start_date, end_date)
        avg_deficit = profile.average_deficit(start_date, end_date)
        days_deficit = profile.days_deficit_on_track(start_date, end_date, tolerance_kcal=200.0)

        # Calculate macro tracking (count records with macros on track)
        days_macros = sum(
            1
            for r in records
            if r.are_macros_on_track(
                profile.macro_split.protein_g,
                profile.macro_split.carbs_g,
                profile.macro_split.fat_g,
                tolerance_grams=10.0,
            )
        )

        # Calculate total days and adherence
        total_days = len(records)
        days_on_track = min(days_deficit, days_macros)
        adherence = (days_on_track / total_days) if total_days > 0 else 0.0

        return ProgressStatisticsType(
            start_date=start_date,
            end_date=end_date,
            weight_delta=weight_delta or 0.0,
            avg_daily_calories=avg_calories,
            avg_calories_burned=None,  # Not tracked yet
            avg_deficit=avg_deficit,
            days_deficit_on_track=days_deficit,
            days_macros_on_track=days_macros,
            total_days=total_days,
            adherence_rate=adherence,
        )
