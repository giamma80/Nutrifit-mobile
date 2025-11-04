"""NutritionalProfile entity - aggregate root for nutritional profiles."""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

from ..exceptions.domain_errors import InvalidUserDataError
from ..value_objects.bmr import BMR
from ..value_objects.goal import Goal
from ..value_objects.macro_split import MacroSplit
from ..value_objects.profile_id import ProfileId
from ..value_objects.tdee import TDEE
from ..value_objects.user_data import UserData
from .progress_record import ProgressRecord


@dataclass
class NutritionalProfile:
    """Nutritional profile aggregate root.

    Represents complete nutritional profile for a user, including:
    - User biometric data (weight, height, age, sex, activity)
    - Calculated metabolic values (BMR, TDEE)
    - Goal-adjusted calorie target
    - Macronutrient distribution
    - Progress tracking history

    This is the aggregate root that enforces consistency boundaries
    and business rules for nutritional profiles.

    Attributes:
        profile_id: Unique profile identifier
        user_id: User this profile belongs to
        user_data: Biometric and activity data
        goal: Nutritional goal (cut/maintain/bulk)
        bmr: Basal Metabolic Rate
        tdee: Total Daily Energy Expenditure
        calories_target: Goal-adjusted calorie target
        macro_split: Protein/carbs/fat distribution
        progress_history: List of progress records
        created_at: Profile creation timestamp
        updated_at: Last update timestamp
    """

    profile_id: ProfileId
    user_id: str
    user_data: UserData
    goal: Goal
    bmr: BMR
    tdee: TDEE
    calories_target: float
    macro_split: MacroSplit
    progress_history: list[ProgressRecord] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        """Validate profile invariants.

        Raises:
            InvalidUserDataError: If validation fails
        """
        self.validate_invariants()

    def validate_invariants(self) -> None:
        """Validate domain invariants.

        Raises:
            InvalidUserDataError: If any invariant is violated
        """
        if not self.user_id or not self.user_id.strip():
            raise InvalidUserDataError("User ID cannot be empty")

        if self.calories_target <= 0:
            raise InvalidUserDataError(
                f"Calories target must be positive, got {self.calories_target}"
            )

        # Verify macro split matches calories target (within 5% tolerance)
        macro_calories = self.macro_split.total_calories()
        tolerance = self.calories_target * 0.05
        if abs(macro_calories - self.calories_target) > tolerance:
            raise InvalidUserDataError(
                f"Macro split ({macro_calories:.0f} kcal) does not match "
                f"calories target ({self.calories_target:.0f} kcal)"
            )

    def update_user_data(
        self,
        weight: Optional[float] = None,
        height: Optional[float] = None,
        age: Optional[int] = None,
        activity_level: Optional[str] = None,
    ) -> None:
        """Update user biometric data.

        Creates new UserData value object with updated values.
        Requires recalculation of BMR/TDEE/macros after update.

        Args:
            weight: New weight in kg (optional)
            height: New height in cm (optional)
            age: New age in years (optional)
            activity_level: New activity level (optional)
        """
        from ..value_objects.activity_level import ActivityLevel

        new_weight = weight if weight is not None else self.user_data.weight
        new_height = height if height is not None else self.user_data.height
        new_age = age if age is not None else self.user_data.age
        new_activity = (
            ActivityLevel(activity_level)
            if activity_level is not None
            else self.user_data.activity_level
        )

        self.user_data = UserData(
            weight=new_weight,
            height=new_height,
            age=new_age,
            sex=self.user_data.sex,
            activity_level=new_activity,
        )
        self.updated_at = datetime.utcnow()

    def update_goal(self, new_goal: Goal) -> None:
        """Update nutritional goal.

        Requires recalculation of calories target and macros after update.

        Args:
            new_goal: New goal (cut/maintain/bulk)
        """
        self.goal = new_goal
        self.updated_at = datetime.utcnow()

    def update_calculations(
        self, bmr: BMR, tdee: TDEE, calories_target: float, macro_split: MacroSplit
    ) -> None:
        """Update calculated values (BMR, TDEE, macros).

        Called after user data or goal changes to refresh calculations.

        Args:
            bmr: New BMR
            tdee: New TDEE
            calories_target: New calorie target
            macro_split: New macro distribution
        """
        self.bmr = bmr
        self.tdee = tdee
        self.calories_target = calories_target
        self.macro_split = macro_split
        self.updated_at = datetime.utcnow()
        self.validate_invariants()

    def record_progress(
        self,
        measurement_date: date,
        weight: float,
        consumed_calories: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> ProgressRecord:
        """Record new progress measurement.

        Creates and adds progress record to history.

        Args:
            measurement_date: Date of measurement
            weight: Weight in kg
            consumed_calories: Optional calories consumed
            notes: Optional user notes

        Returns:
            ProgressRecord: Created progress record
        """
        record = ProgressRecord.create(
            profile_id=self.profile_id,
            date=measurement_date,
            weight=weight,
            consumed_calories=consumed_calories,
            notes=notes,
        )
        self.progress_history.append(record)
        self.updated_at = datetime.utcnow()
        return record

    def get_progress_by_date(self, measurement_date: date) -> Optional[ProgressRecord]:
        """Get progress record for specific date.

        Args:
            measurement_date: Date to search for

        Returns:
            Optional[ProgressRecord]: Record if found, None otherwise
        """
        return next((r for r in self.progress_history if r.date == measurement_date), None)

    def get_progress_range(self, start_date: date, end_date: date) -> list[ProgressRecord]:
        """Get progress records within date range.

        Args:
            start_date: Range start (inclusive)
            end_date: Range end (inclusive)

        Returns:
            list[ProgressRecord]: Records in range, sorted by date
        """
        records = [r for r in self.progress_history if start_date <= r.date <= end_date]
        return sorted(records, key=lambda r: r.date)

    def calculate_weight_delta(self, start_date: date, end_date: date) -> Optional[float]:
        """Calculate weight change in date range.

        Args:
            start_date: Range start
            end_date: Range end

        Returns:
            Optional[float]: Weight delta in kg, None if insufficient data
        """
        records = self.get_progress_range(start_date, end_date)
        if len(records) < 2:
            return None

        first_weight = records[0].weight
        last_weight = records[-1].weight
        return last_weight - first_weight

    def calculate_target_weight_delta(self, days: int) -> float:
        """Calculate target weight change for goal over days.

        Based on calorie deficit/surplus and 7700 kcal = 1 kg rule.

        Args:
            days: Number of days

        Returns:
            float: Expected weight change in kg

        Example:
            >>> profile.goal = Goal.CUT
            >>> profile.calories_target = 2000  # -500 from TDEE
            >>> profile.calculate_target_weight_delta(7)
            -0.45  # ~0.5 kg loss per week
        """
        daily_deficit = self.tdee.value - self.calories_target
        total_deficit = daily_deficit * days
        weight_delta = total_deficit / 7700  # 7700 kcal = 1 kg
        return weight_delta

    def average_daily_calories(self, start_date: date, end_date: date) -> Optional[float]:
        """Calculate average daily calories consumed in range.

        Args:
            start_date: Range start
            end_date: Range end

        Returns:
            Optional[float]: Average daily calories, None if no data
        """
        records = self.get_progress_range(start_date, end_date)
        calories_records = [r.consumed_calories for r in records if r.consumed_calories is not None]

        if not calories_records:
            return None

        return sum(calories_records) / len(calories_records)

    def days_on_track(
        self, start_date: date, end_date: date, tolerance_percentage: float = 0.1
    ) -> int:
        """Count days within calorie target tolerance (static TDEE).

        NOTE: For dynamic deficit tracking, use days_deficit_on_track().

        Args:
            start_date: Range start
            end_date: Range end
            tolerance_percentage: Tolerance fraction (default 10%)

        Returns:
            int: Number of days on track
        """
        records = self.get_progress_range(start_date, end_date)
        return sum(1 for r in records if r.is_on_track(self.calories_target, tolerance_percentage))

    def days_deficit_on_track(
        self,
        start_date: date,
        end_date: date,
        tolerance_kcal: float = 50.0,
    ) -> int:
        """Count days where actual deficit matches target deficit.

        This is the PRIMARY metric for goal adherence. Uses actual
        burned calories to determine if the deficit/surplus goal is met.

        Args:
            start_date: Range start
            end_date: Range end
            tolerance_kcal: Absolute tolerance in kcal (default 50)

        Returns:
            int: Number of days on track with deficit goal

        Example:
            >>> profile.goal = Goal.CUT  # -500 kcal target
            >>> profile.days_deficit_on_track(start, end)
            18  # 18 days achieved ~500 kcal deficit
        """
        records = self.get_progress_range(start_date, end_date)
        target_deficit = self.goal.target_deficit()
        return sum(1 for r in records if r.is_deficit_on_track(target_deficit, tolerance_kcal))

    def average_deficit(self, start_date: date, end_date: date) -> Optional[float]:
        """Calculate average daily calorie balance (deficit/surplus).

        Args:
            start_date: Range start
            end_date: Range end

        Returns:
            Optional[float]: Average deficit (negative) or surplus
                           (positive), None if no data

        Example:
            >>> profile.average_deficit(start, end)
            -485.5  # Average 485.5 kcal deficit per day
        """
        records = self.get_progress_range(start_date, end_date)
        balances = [r.calorie_balance for r in records if r.calorie_balance is not None]

        if not balances:
            return None

        return sum(balances) / len(balances)

    def __str__(self) -> str:
        """String representation.

        Returns:
            str: Profile summary
        """
        return (
            f"Profile {self.profile_id} - User {self.user_id} - "
            f"Goal: {self.goal.value} - Target: {self.calories_target:.0f} kcal"
        )

    def __repr__(self) -> str:
        """Developer-friendly representation.

        Returns:
            str: Full profile details
        """
        return (
            f"NutritionalProfile(profile_id={self.profile_id}, "
            f"user_id={self.user_id}, goal={self.goal}, "
            f"calories_target={self.calories_target})"
        )
