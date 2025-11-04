"""TDEEService - Total Daily Energy Expenditure calculation."""

from ..core.ports.calculators import ITDEECalculator
from ..core.value_objects.activity_level import ActivityLevel
from ..core.value_objects.bmr import BMR
from ..core.value_objects.tdee import TDEE


class TDEEService(ITDEECalculator):
    """Calculate Total Daily Energy Expenditure.

    TDEE represents total calories burned per day, calculated by
    multiplying BMR by Physical Activity Level (PAL) multiplier.

    Formula:
        TDEE = BMR × PAL

    PAL Multipliers:
        - Sedentary: 1.2 (little/no exercise)
        - Light: 1.375 (light exercise 1-3 days/week)
        - Moderate: 1.55 (moderate exercise 3-5 days/week)
        - Active: 1.725 (hard exercise 6-7 days/week)
        - Very Active: 1.9 (very hard exercise + physical job)
    """

    def calculate(self, bmr: BMR, activity_level: ActivityLevel) -> TDEE:
        """Calculate TDEE from BMR and activity level.

        Args:
            bmr: Basal metabolic rate
            activity_level: Physical activity level

        Returns:
            TDEE: Total daily energy expenditure in kcal/day

        Example:
            >>> service = TDEEService()
            >>> bmr = BMR(value=1780.0)
            >>> activity = ActivityLevel.MODERATE
            >>> tdee = service.calculate(bmr, activity)
            >>> tdee.value
            2759.0  # 1780 × 1.55
        """
        pal_multiplier = activity_level.pal_multiplier()
        tdee_value = bmr.value * pal_multiplier

        return TDEE(value=tdee_value)
