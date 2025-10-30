"""TDEE value object - Total Daily Energy Expenditure."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TDEE:
    """Total Daily Energy Expenditure in kcal/day.
    
    Represents total calories burned per day including:
    - BMR (Basal Metabolic Rate)
    - Physical activity
    - Thermic effect of food
    - Non-exercise activity thermogenesis (NEAT)
    
    Calculated as: TDEE = BMR × PAL (Physical Activity Level)
    
    Attributes:
        value: TDEE in kcal/day (must be positive)
    """
    
    value: float
    
    def __post_init__(self) -> None:
        """Validate TDEE is positive.
        
        Raises:
            ValueError: If TDEE is not positive
        """
        if self.value <= 0:
            raise ValueError(f"TDEE must be positive, got {self.value}")
    
    def __str__(self) -> str:
        """String representation.
        
        Returns:
            str: TDEE with unit
        """
        return f"{self.value:.0f} kcal/day"
    
    def __repr__(self) -> str:
        """Developer-friendly representation.
        
        Returns:
            str: TDEE with value
        """
        return f"TDEE(value={self.value})"
