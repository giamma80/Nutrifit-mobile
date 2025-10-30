"""ProgressRecord entity - single weight/progress measurement."""

from dataclasses import dataclass, field
from datetime import date, datetime
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
        tdee_estimate: Optional adaptive TDEE (Step 2 ML)
        notes: Optional user notes
        created_at: Creation timestamp
    """
    
    record_id: UUID
    profile_id: ProfileId
    date: date
    weight: float
    consumed_calories: Optional[float] = None
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
                f"Consumed calories must be non-negative, "
                f"got {self.consumed_calories}"
            )
        
        if self.tdee_estimate is not None and self.tdee_estimate <= 0:
            raise ValueError(
                f"TDEE estimate must be positive, got {self.tdee_estimate}"
            )
    
    @staticmethod
    def create(
        profile_id: ProfileId,
        date: date,
        weight: float,
        consumed_calories: Optional[float] = None,
        notes: Optional[str] = None
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
            notes=notes
        )
    
    def update_consumed_calories(self, calories: float) -> None:
        """Update consumed calories (e.g., from meal events).
        
        Args:
            calories: Total calories consumed on this date
        """
        if calories < 0:
            raise ValueError(
                f"Consumed calories must be non-negative, got {calories}"
            )
        self.consumed_calories = calories
    
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
        self,
        target_calories: float,
        tolerance_percentage: float = 0.1
    ) -> Optional[bool]:
        """Check if consumed calories are within tolerance of target.
        
        Args:
            target_calories: Target daily calories
            tolerance_percentage: Tolerance as fraction (default 10%)
            
        Returns:
            Optional[bool]: True if on track, None if no calorie data
        """
        if self.consumed_calories is None:
            return None
        
        delta = abs(self.consumed_calories - target_calories)
        tolerance = target_calories * tolerance_percentage
        return delta <= tolerance
    
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
