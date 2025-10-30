"""Calculator ports - interfaces for BMR/TDEE/Macro calculations."""

from abc import ABC, abstractmethod

from ..value_objects.activity_level import ActivityLevel
from ..value_objects.bmr import BMR
from ..value_objects.goal import Goal
from ..value_objects.macro_split import MacroSplit
from ..value_objects.tdee import TDEE
from ..value_objects.user_data import UserData


class IBMRCalculator(ABC):
    """Port for BMR calculation.
    
    Calculates Basal Metabolic Rate using Mifflin-St Jeor formula.
    """
    
    @abstractmethod
    def calculate(self, user_data: UserData) -> BMR:
        """Calculate BMR from user data.
        
        Args:
            user_data: User biometric data
            
        Returns:
            BMR: Calculated basal metabolic rate
        """
        pass


class ITDEECalculator(ABC):
    """Port for TDEE calculation.
    
    Calculates Total Daily Energy Expenditure from BMR and activity.
    """
    
    @abstractmethod
    def calculate(self, bmr: BMR, activity_level: ActivityLevel) -> TDEE:
        """Calculate TDEE from BMR and activity level.
        
        Args:
            bmr: Basal metabolic rate
            activity_level: Physical activity level
            
        Returns:
            TDEE: Total daily energy expenditure
        """
        pass


class IMacroCalculator(ABC):
    """Port for macronutrient distribution calculation.
    
    Calculates protein/carbs/fat split based on goal and calories.
    """
    
    @abstractmethod
    def calculate(
        self,
        calories_target: float,
        weight: float,
        goal: Goal
    ) -> MacroSplit:
        """Calculate macro distribution.
        
        Args:
            calories_target: Daily calorie target
            weight: Body weight in kg
            goal: Nutritional goal
            
        Returns:
            MacroSplit: Protein/carbs/fat in grams
        """
        pass
