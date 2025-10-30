"""NutritionalProfileFactory - factory for creating profiles."""

from datetime import date

from ..entities.nutritional_profile import NutritionalProfile
from ..value_objects.bmr import BMR
from ..value_objects.goal import Goal
from ..value_objects.macro_split import MacroSplit
from ..value_objects.profile_id import ProfileId
from ..value_objects.tdee import TDEE
from ..value_objects.user_data import UserData


class NutritionalProfileFactory:
    """Factory for creating NutritionalProfile entities.
    
    Encapsulates complex creation logic and enforces consistency.
    """
    
    @staticmethod
    def create(
        user_id: str,
        user_data: UserData,
        goal: Goal,
        bmr: BMR,
        tdee: TDEE,
        calories_target: float,
        macro_split: MacroSplit,
        initial_weight: float,
        initial_date: date
    ) -> NutritionalProfile:
        """Create new nutritional profile with initial progress record.
        
        Args:
            user_id: User identifier
            user_data: Biometric and activity data
            goal: Nutritional goal
            bmr: Calculated BMR
            tdee: Calculated TDEE
            calories_target: Goal-adjusted calorie target
            macro_split: Macro distribution
            initial_weight: Starting weight
            initial_date: Starting date
            
        Returns:
            NutritionalProfile: New profile with initial progress record
        """
        profile_id = ProfileId.generate()
        
        profile = NutritionalProfile(
            profile_id=profile_id,
            user_id=user_id,
            user_data=user_data,
            goal=goal,
            bmr=bmr,
            tdee=tdee,
            calories_target=calories_target,
            macro_split=macro_split
        )
        
        # Add initial progress record
        profile.record_progress(
            measurement_date=initial_date,
            weight=initial_weight,
            notes="Initial measurement"
        )
        
        return profile
    
    @staticmethod
    def create_without_progress(
        user_id: str,
        user_data: UserData,
        goal: Goal,
        bmr: BMR,
        tdee: TDEE,
        calories_target: float,
        macro_split: MacroSplit
    ) -> NutritionalProfile:
        """Create profile without initial progress record.
        
        Use when progress will be added later.
        
        Args:
            user_id: User identifier
            user_data: Biometric and activity data
            goal: Nutritional goal
            bmr: Calculated BMR
            tdee: Calculated TDEE
            calories_target: Goal-adjusted calorie target
            macro_split: Macro distribution
            
        Returns:
            NutritionalProfile: New profile without progress history
        """
        profile_id = ProfileId.generate()
        
        return NutritionalProfile(
            profile_id=profile_id,
            user_id=user_id,
            user_data=user_data,
            goal=goal,
            bmr=bmr,
            tdee=tdee,
            calories_target=calories_target,
            macro_split=macro_split
        )
