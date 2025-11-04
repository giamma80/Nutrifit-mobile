"""ProgressRecord entity - single weight/progress measurement."""

from dataclasses import dataclass, field
from datetime import date as DateType
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from ..value_objects.profile_id import ProfileId


@dataclass
class ProgressRecord:
    """Single progress measurement for weight tracking.

    Entity representing a point-in-time measurement of user progress,
    including weight, consumed calories, and optional notes.

    Attributes:
        record_id: Unique identifier for this record
        profile_id: Reference to owning profile
        date: Date of measurement
        weight: Weight in kg
        consumed_calories: Optional calories consumed (from meals)
        consumed_protein_g: Optional protein consumed in grams
        consumed_carbs_g: Optional carbs consumed in grams
        consumed_fat_g: Optional fat consumed in grams
        calories_burned_bmr: Optional BMR calories for the day
        calories_burned_active: Optional active calories (from activities)
        tdee_estimate: Optional adaptive TDEE (Step 2 ML)
        notes: Optional user notes
        created_at: Creation timestamp
    """

    record_id: UUID
    profile_id: ProfileId
    date: DateType
    weight: float
    consumed_calories: Optional[float] = None
    consumed_protein_g: Optional[float] = None
    consumed_carbs_g: Optional[float] = None
    consumed_fat_g: Optional[float] = None
    calories_burned_bmr: Optional[float] = None
    calories_burned_active: Optional[float] = None
    tdee_estimate: Optional[float] = None
    notes: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        """Validate progress record data.

        Raises:
            ValueError: If validation fails
        """
        if self.weight <= 0:
            raise ValueError(f"Weight must be positive, got {self.weight}")

        if self.consumed_calories is not None and self.consumed_calories < 0:
            raise ValueError(
                f"Consumed calories must be non-negative, " f"got {self.consumed_calories}"
            )

        if self.consumed_protein_g is not None and self.consumed_protein_g < 0:
            raise ValueError(
                f"Consumed protein must be non-negative, " f"got {self.consumed_protein_g}"
            )

        if self.consumed_carbs_g is not None and self.consumed_carbs_g < 0:
            raise ValueError(
                f"Consumed carbs must be non-negative, " f"got {self.consumed_carbs_g}"
            )

        if self.consumed_fat_g is not None and self.consumed_fat_g < 0:
            raise ValueError(f"Consumed fat must be non-negative, " f"got {self.consumed_fat_g}")

        if self.calories_burned_bmr is not None and self.calories_burned_bmr < 0:
            raise ValueError(
                f"BMR calories must be non-negative, " f"got {self.calories_burned_bmr}"
            )

        if self.calories_burned_active is not None and self.calories_burned_active < 0:
            raise ValueError(
                f"Active calories must be non-negative, " f"got {self.calories_burned_active}"
            )

        if self.tdee_estimate is not None and self.tdee_estimate <= 0:
            raise ValueError(f"TDEE estimate must be positive, " f"got {self.tdee_estimate}")

    @staticmethod
    def create(
        profile_id: ProfileId,
        date: DateType,
        weight: float,
        consumed_calories: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> "ProgressRecord":
        """Factory method to create new progress record.

        Args:
            profile_id: Profile this record belongs to
            date: Measurement date
            weight: Weight in kg
            consumed_calories: Optional calories consumed
            notes: Optional user notes

        Returns:
            ProgressRecord: New progress record
        """
        return ProgressRecord(
            record_id=uuid4(),
            profile_id=profile_id,
            date=date,
            weight=weight,
            consumed_calories=consumed_calories,
            notes=notes,
        )

    def update_consumed_calories(self, calories: float) -> None:
        """Update consumed calories (e.g., from meal events).

        Args:
            calories: Total calories consumed on this date
        """
        if calories < 0:
            raise ValueError(f"Consumed calories must be non-negative, got {calories}")
        self.consumed_calories = calories

    def update_consumed_macros(self, protein_g: float, carbs_g: float, fat_g: float) -> None:
        """Update consumed macronutrients.

        Args:
            protein_g: Protein consumed in grams
            carbs_g: Carbohydrates consumed in grams
            fat_g: Fat consumed in grams

        Raises:
            ValueError: If any macro is negative
        """
        if protein_g < 0:
            raise ValueError(f"Protein must be non-negative, got {protein_g}")
        if carbs_g < 0:
            raise ValueError(f"Carbs must be non-negative, got {carbs_g}")
        if fat_g < 0:
            raise ValueError(f"Fat must be non-negative, got {fat_g}")

        self.consumed_protein_g = protein_g
        self.consumed_carbs_g = carbs_g
        self.consumed_fat_g = fat_g

        # Auto-calculate calories from macros (P×4 + C×4 + F×9)
        self.consumed_calories = (protein_g * 4) + (carbs_g * 4) + (fat_g * 9)

    def update_burned_calories(self, bmr_calories: float, active_calories: float) -> None:
        """Update calories burned (BMR + active).

        Args:
            bmr_calories: Basal metabolic rate calories for the day
            active_calories: Calories burned from activities
        """
        if bmr_calories < 0:
            raise ValueError(f"BMR calories must be non-negative, got {bmr_calories}")
        if active_calories < 0:
            raise ValueError(f"Active calories must be non-negative, " f"got {active_calories}")
        self.calories_burned_bmr = bmr_calories
        self.calories_burned_active = active_calories

    @property
    def calories_burned_total(self) -> Optional[float]:
        """Total calories burned (BMR + active).

        Returns:
            Optional[float]: Total burned, or None if data incomplete
        """
        if self.calories_burned_bmr is not None and self.calories_burned_active is not None:
            return self.calories_burned_bmr + self.calories_burned_active
        return None

    @property
    def calorie_balance(self) -> Optional[float]:
        """Net calorie balance (consumed - burned).

        Positive = calorie surplus
        Negative = calorie deficit

        Returns:
            Optional[float]: Net balance, or None if data incomplete
        """
        if self.consumed_calories is not None and self.calories_burned_total is not None:
            return self.consumed_calories - self.calories_burned_total
        return None

    def calorie_delta(self, target_calories: float) -> Optional[float]:
        """Calculate difference between consumed and target calories.

        Args:
            target_calories: Target daily calories

        Returns:
            Optional[float]: Delta (consumed - target), or None if no data

        Example:
            >>> record.consumed_calories = 2250.0
            >>> record.calorie_delta(2259.0)
            -9.0  # Under target by 9 kcal
        """
        if self.consumed_calories is None:
            return None
        return self.consumed_calories - target_calories

    def is_on_track(
        self, target_calories: float, tolerance_percentage: float = 0.1
    ) -> Optional[bool]:
        """Check if consumed calories are within tolerance of target.

        NOTE: This uses static TDEE target. For dynamic deficit tracking,
        use is_deficit_on_track() instead.

        Args:
            target_calories: Target daily calories (from TDEE)
            tolerance_percentage: Tolerance as fraction (default 10%)

        Returns:
            Optional[bool]: True if on track, None if no calorie data
        """
        if self.consumed_calories is None:
            return None

        delta = abs(self.consumed_calories - target_calories)
        tolerance = target_calories * tolerance_percentage
        return delta <= tolerance

    def is_deficit_on_track(
        self, target_deficit: float, tolerance_kcal: float = 50.0
    ) -> Optional[bool]:
        """Check if actual calorie balance matches target deficit.

        This is the PRIMARY validation method for goal tracking.
        Uses actual burned calories to determine if deficit/surplus
        goal is being met.

        Args:
            target_deficit: Target daily deficit (negative for cut,
                           positive for bulk, 0 for maintain)
            tolerance_kcal: Absolute tolerance in kcal (default 50)

        Returns:
            Optional[bool]: True if on track, None if data incomplete

        Example:
            >>> record.consumed_calories = 2300
            >>> record.calories_burned_total = 2800
            >>> record.calorie_balance  # -500 (deficit)
            >>> record.is_deficit_on_track(-500, tolerance_kcal=50)
            True  # Within 50 kcal of target -500
        """
        if self.calorie_balance is None:
            return None

        # Check if actual balance is within tolerance of target
        delta = abs(self.calorie_balance - target_deficit)
        return delta <= tolerance_kcal

    def macro_protein_delta(self, target_protein_g: float) -> Optional[float]:
        """Calculate protein delta from target.

        Args:
            target_protein_g: Target daily protein in grams

        Returns:
            Optional[float]: Delta (consumed - target), None if no data
        """
        if self.consumed_protein_g is None:
            return None
        return self.consumed_protein_g - target_protein_g

    def macro_carbs_delta(self, target_carbs_g: float) -> Optional[float]:
        """Calculate carbs delta from target.

        Args:
            target_carbs_g: Target daily carbs in grams

        Returns:
            Optional[float]: Delta (consumed - target), None if no data
        """
        if self.consumed_carbs_g is None:
            return None
        return self.consumed_carbs_g - target_carbs_g

    def macro_fat_delta(self, target_fat_g: float) -> Optional[float]:
        """Calculate fat delta from target.

        Args:
            target_fat_g: Target daily fat in grams

        Returns:
            Optional[float]: Delta (consumed - target), None if no data
        """
        if self.consumed_fat_g is None:
            return None
        return self.consumed_fat_g - target_fat_g

    def are_macros_on_track(
        self,
        target_protein_g: float,
        target_carbs_g: float,
        target_fat_g: float,
        tolerance_grams: float = 10.0,
    ) -> Optional[bool]:
        """Check if all macros are within tolerance.

        Args:
            target_protein_g: Target protein in grams
            target_carbs_g: Target carbs in grams
            target_fat_g: Target fat in grams
            tolerance_grams: Tolerance in grams for each macro (default 10g)

        Returns:
            Optional[bool]: True if all macros on track,
                           None if data incomplete

        Example:
            >>> record.consumed_protein_g = 178
            >>> record.consumed_carbs_g = 245
            >>> record.consumed_fat_g = 65
            >>> record.are_macros_on_track(176, 248, 63, tolerance_grams=10)
            True  # All within 10g
        """
        if (
            self.consumed_protein_g is None
            or self.consumed_carbs_g is None
            or self.consumed_fat_g is None
        ):
            return None

        protein_ok = abs(self.consumed_protein_g - target_protein_g) <= tolerance_grams
        carbs_ok = abs(self.consumed_carbs_g - target_carbs_g) <= tolerance_grams
        fat_ok = abs(self.consumed_fat_g - target_fat_g) <= tolerance_grams

        return protein_ok and carbs_ok and fat_ok

    def __str__(self) -> str:
        """String representation.

        Returns:
            str: Date and weight
        """
        return f"{self.date}: {self.weight:.1f}kg"

    def __repr__(self) -> str:
        """Developer-friendly representation.

        Returns:
            str: Full record details
        """
        return (
            f"ProgressRecord(record_id={self.record_id}, "
            f"date={self.date}, weight={self.weight}kg, "
            f"consumed_calories={self.consumed_calories})"
        )
