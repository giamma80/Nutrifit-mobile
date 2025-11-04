"""ActivityLevel value object - physical activity level for TDEE."""

from enum import Enum


class ActivityLevel(str, Enum):
    """Physical Activity Level (PAL) for TDEE calculation.

    Represents user's typical activity level to multiply BMR:
    - SEDENTARY: Little or no exercise (office job)
    - LIGHT: Light exercise 1-3 days/week
    - MODERATE: Moderate exercise 3-5 days/week
    - ACTIVE: Hard exercise 6-7 days/week
    - VERY_ACTIVE: Very hard exercise + physical job
    """

    SEDENTARY = "sedentary"
    LIGHT = "light"
    MODERATE = "moderate"
    ACTIVE = "active"
    VERY_ACTIVE = "very_active"

    def pal_multiplier(self) -> float:
        """Get PAL (Physical Activity Level) multiplier.

        Returns:
            float: Multiplier for BMR to calculate TDEE

        Example:
            >>> ActivityLevel.MODERATE.pal_multiplier()
            1.55
        """
        multipliers = {
            ActivityLevel.SEDENTARY: 1.2,  # Minimal activity
            ActivityLevel.LIGHT: 1.375,  # Light exercise
            ActivityLevel.MODERATE: 1.55,  # Moderate exercise
            ActivityLevel.ACTIVE: 1.725,  # Hard exercise
            ActivityLevel.VERY_ACTIVE: 1.9,  # Very hard exercise
        }
        return multipliers[self]

    def description(self) -> str:
        """Get human-readable description.

        Returns:
            str: Activity level description
        """
        descriptions = {
            ActivityLevel.SEDENTARY: "Little or no exercise",
            ActivityLevel.LIGHT: "Light exercise 1-3 days/week",
            ActivityLevel.MODERATE: "Moderate exercise 3-5 days/week",
            ActivityLevel.ACTIVE: "Hard exercise 6-7 days/week",
            ActivityLevel.VERY_ACTIVE: "Very hard exercise + physical job",
        }
        return descriptions[self]
