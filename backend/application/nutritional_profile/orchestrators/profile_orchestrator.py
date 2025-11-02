"""ProfileOrchestrator - coordinates calculation services."""

from dataclasses import dataclass

from domain.nutritional_profile.calculation.bmr_service import BMRService
from domain.nutritional_profile.calculation.macro_service import MacroService
from domain.nutritional_profile.calculation.tdee_service import TDEEService
from domain.nutritional_profile.core.value_objects.bmr import BMR
from domain.nutritional_profile.core.value_objects.goal import Goal
from domain.nutritional_profile.core.value_objects.macro_split import (
    MacroSplit,
)
from domain.nutritional_profile.core.value_objects.tdee import TDEE
from domain.nutritional_profile.core.value_objects.user_data import UserData


@dataclass(frozen=True)
class ProfileCalculations:
    """Result of profile calculations."""

    bmr: BMR
    tdee: TDEE
    calories_target: float
    macro_split: MacroSplit


class ProfileOrchestrator:
    """
    Orchestrates calculation services for nutritional profiles.

    Flow:
    1. Calculate BMR from user's biometric data
    2. Calculate TDEE from BMR and activity level
    3. Apply goal adjustments to get target calories
    4. Calculate macro distribution based on goal and weight
    """

    def __init__(
        self,
        bmr_service: BMRService,
        tdee_service: TDEEService,
        macro_service: MacroService,
    ):
        self._bmr_service = bmr_service
        self._tdee_service = tdee_service
        self._macro_service = macro_service

    def calculate_profile_metrics(
        self,
        user_data: UserData,
        goal: Goal,
    ) -> ProfileCalculations:
        """
        Calculate complete nutritional profile metrics.

        Args:
            user_data: User's biometric data with activity level
            goal: Nutritional goal (cut/maintain/bulk)

        Returns:
            ProfileCalculations with all computed metrics

        Raises:
            ValueError: If calculations fail due to invalid inputs
        """
        # Step 1: Calculate BMR (basal metabolic rate)
        bmr = self._bmr_service.calculate(user_data=user_data)

        # Step 2: Calculate TDEE (total daily energy expenditure)
        tdee = self._tdee_service.calculate(
            bmr=bmr,
            activity_level=user_data.activity_level,
        )

        # Step 3: Apply goal adjustment to get target calories
        calories_target = goal.calorie_adjustment(tdee.value)

        # Step 4: Calculate macro distribution
        macro_split = self._macro_service.calculate(
            calories_target=calories_target,
            weight=user_data.weight,
            goal=goal,
        )

        return ProfileCalculations(
            bmr=bmr,
            tdee=tdee,
            calories_target=calories_target,
            macro_split=macro_split,
        )

    def recalculate_metrics(
        self,
        user_data: UserData,
        goal: Goal,
    ) -> ProfileCalculations:
        """
        Recalculate metrics when profile is updated.

        This is an alias for calculate_profile_metrics to make intent
        clear when updating existing profiles.

        Args:
            user_data: Updated user biometric data with activity level
            goal: Updated or existing goal

        Returns:
            ProfileCalculations with recalculated metrics
        """
        return self.calculate_profile_metrics(user_data, goal)
