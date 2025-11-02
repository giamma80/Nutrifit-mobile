"""GraphQL types for nutritional profile domain.

These types support the Nutritional Profile feature with personalized
BMR/TDEE calculation, macronutrient distribution, and progress tracking.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional, List
from datetime import date, datetime
import strawberry


__all__ = [
    # Enums
    "SexEnum",
    "ActivityLevelEnum",
    "GoalEnum",
    # Output types
    "BMRType",
    "TDEEType",
    "MacroSplitType",
    "ProgressRecordType",
    "NutritionalProfileType",
    "ProgressStatisticsType",
    # Input types
    "UserDataInput",
    "CreateProfileInput",
    "UpdateProfileInput",
    "RecordProgressInput",
]


# ============================================
# ENUMS
# ============================================


@strawberry.enum
class SexEnum(str, Enum):
    """Biological sex for BMR calculation."""

    M = "M"  # Male
    F = "F"  # Female


@strawberry.enum
class ActivityLevelEnum(str, Enum):
    """Physical Activity Level (PAL) for TDEE calculation."""

    SEDENTARY = "sedentary"  # Little or no exercise
    LIGHT = "light"  # Light exercise 1-3 days/week
    MODERATE = "moderate"  # Moderate exercise 3-5 days/week
    ACTIVE = "active"  # Hard exercise 6-7 days/week
    VERY_ACTIVE = "very_active"  # Very hard exercise + physical job


@strawberry.enum
class GoalEnum(str, Enum):
    """User's nutritional goal."""

    CUT = "cut"  # Weight loss with calorie deficit
    MAINTAIN = "maintain"  # Weight maintenance at TDEE
    BULK = "bulk"  # Muscle gain with calorie surplus


# ============================================
# OUTPUT TYPES
# ============================================


@strawberry.type
class BMRType:
    """Basal Metabolic Rate (BMR) - calories burned at rest."""

    value: float  # kcal/day

    def description(self) -> str:
        """Human-readable BMR description."""
        return f"{self.value:.0f} kcal/day (at rest)"


@strawberry.type
class TDEEType:
    """Total Daily Energy Expenditure (TDEE) - calories burned with activity."""  # noqa: E501

    value: float  # kcal/day
    activity_level: ActivityLevelEnum

    def description(self) -> str:
        """Human-readable TDEE description."""
        return f"{self.value:.0f} kcal/day ({self.activity_level.value})"


@strawberry.type
class MacroSplitType:
    """Macronutrient distribution (protein, carbs, fat) in grams."""

    protein_g: int  # grams
    carbs_g: int  # grams
    fat_g: int  # grams

    def total_calories(self) -> float:
        """Calculate total calories from macros (4-4-9 rule)."""
        return (self.protein_g * 4) + (self.carbs_g * 4) + (self.fat_g * 9)

    def protein_percentage(self) -> float:
        """Protein percentage of total calories."""
        total = self.total_calories()
        if total == 0:
            return 0.0
        return (self.protein_g * 4) / total * 100

    def carbs_percentage(self) -> float:
        """Carbs percentage of total calories."""
        total = self.total_calories()
        if total == 0:
            return 0.0
        return (self.carbs_g * 4) / total * 100

    def fat_percentage(self) -> float:
        """Fat percentage of total calories."""
        total = self.total_calories()
        if total == 0:
            return 0.0
        return (self.fat_g * 9) / total * 100

    def summary(self) -> str:
        """Human-readable macro summary."""
        return f"{self.protein_g}P / {self.carbs_g}C / {self.fat_g}F"


@strawberry.type
class ProgressRecordType:
    """Daily progress record with weight, calories, and macros tracking."""

    date: date  # YYYY-MM-DD
    weight: float  # kg
    consumed_calories: Optional[float] = None  # kcal consumed
    consumed_protein_g: Optional[float] = None  # grams
    consumed_carbs_g: Optional[float] = None  # grams
    consumed_fat_g: Optional[float] = None  # grams
    calories_burned_bmr: Optional[float] = None  # kcal (BMR component)
    calories_burned_active: Optional[float] = None  # kcal (activity component)  # noqa: E501
    notes: Optional[str] = None

    def calories_burned_total(self) -> Optional[float]:
        """Total calories burned (BMR + active)."""
        if self.calories_burned_bmr is None:
            return None
        active = self.calories_burned_active or 0.0
        return self.calories_burned_bmr + active

    def calorie_balance(self) -> Optional[float]:
        """Calorie balance (consumed - burned). Negative = deficit."""
        if self.consumed_calories is None:
            return None
        burned = self.calories_burned_total()
        if burned is None:
            return None
        return self.consumed_calories - burned


@strawberry.type
class NutritionalProfileType:
    """Complete nutritional profile with calculations and progress."""

    profile_id: str
    user_id: str
    user_data: "UserDataType"
    goal: GoalEnum
    bmr: BMRType
    tdee: TDEEType
    calories_target: float  # kcal/day adjusted for goal
    macro_split: MacroSplitType
    progress_history: List[ProgressRecordType]
    created_at: datetime
    updated_at: datetime

    def latest_weight(self) -> Optional[float]:
        """Get most recent weight from progress history."""
        if not self.progress_history:
            return None
        # Assume sorted by date desc
        return self.progress_history[0].weight

    def weight_change(self) -> Optional[float]:
        """Calculate weight change (latest - oldest)."""
        if len(self.progress_history) < 2:
            return None
        latest = self.progress_history[0].weight
        oldest = self.progress_history[-1].weight
        return latest - oldest


@strawberry.type
class UserDataType:
    """User biometric and activity data."""

    weight: float  # kg
    height: float  # cm
    age: int  # years
    sex: SexEnum
    activity_level: ActivityLevelEnum

    def bmi(self) -> float:
        """Calculate Body Mass Index."""
        height_m = self.height / 100.0
        return self.weight / (height_m**2)

    def bmi_category(self) -> str:
        """Get BMI category."""
        bmi_value = self.bmi()
        if bmi_value < 18.5:
            return "underweight"
        elif bmi_value < 25.0:
            return "normal"
        elif bmi_value < 30.0:
            return "overweight"
        else:
            return "obese"


@strawberry.type
class ProgressStatisticsType:
    """Progress analytics over a time period."""

    start_date: date
    end_date: date
    weight_delta: float  # kg (negative = weight loss)
    avg_daily_calories: Optional[float] = None  # kcal/day consumed
    avg_calories_burned: Optional[float] = None  # kcal/day burned
    avg_deficit: Optional[float] = None  # kcal/day (negative = deficit)
    days_deficit_on_track: int = 0  # days within target deficit ±200
    days_macros_on_track: int = 0  # days with macros within ±10%
    total_days: int = 0
    adherence_rate: float = 0.0  # % days on track (combined deficit + macros)

    def weekly_weight_loss_rate(self) -> Optional[float]:
        """Calculate weekly weight loss rate (kg/week)."""
        if self.total_days == 0:
            return None
        weeks = self.total_days / 7.0
        if weeks == 0:
            return None
        return self.weight_delta / weeks


# ============================================
# INPUT TYPES
# ============================================


@strawberry.input
class UserDataInput:
    """User biometric and activity data input."""

    weight: float  # kg (30-300)
    height: float  # cm (100-250)
    age: int  # years (18-120)
    sex: SexEnum
    activity_level: ActivityLevelEnum


@strawberry.input
class CreateProfileInput:
    """Input for creating a nutritional profile."""

    user_id: str
    user_data: UserDataInput
    goal: GoalEnum
    initial_weight: float  # kg
    initial_date: Optional[date] = None  # defaults to today


@strawberry.input
class UpdateProfileInput:
    """Input for updating a nutritional profile."""

    profile_id: str
    user_data: Optional[UserDataInput] = None  # update biometrics
    goal: Optional[GoalEnum] = None  # change goal


@strawberry.input
class RecordProgressInput:
    """Input for recording daily progress."""

    profile_id: str
    date: date
    weight: float  # kg
    consumed_calories: Optional[float] = None  # kcal
    consumed_protein_g: Optional[float] = None  # grams
    consumed_carbs_g: Optional[float] = None  # grams
    consumed_fat_g: Optional[float] = None  # grams
    calories_burned_bmr: Optional[float] = None  # kcal (BMR component)
    calories_burned_active: Optional[float] = None  # kcal (activity)
    notes: Optional[str] = None
