"""BMR value object - Basal Metabolic Rate."""

from dataclasses import dataclass


@dataclass(frozen=True)
class BMR:
    """Basal Metabolic Rate in kcal/day.
    
    Represents the minimum calories needed for basic bodily functions
    at rest (breathing, circulation, cell production, nutrient processing).
    
    Attributes:
        value: BMR in kcal/day (must be positive)
    """
    
    value: float
    
    def __post_init__(self) -> None:
        """Validate BMR is positive.
        
        Raises:
            ValueError: If BMR is not positive
        """
        if self.value <= 0:
            raise ValueError(f"BMR must be positive, got {self.value}")
    
    def __str__(self) -> str:
        """String representation.
        
        Returns:
            str: BMR with unit
        """
        return f"{self.value:.0f} kcal/day"
    
    def __repr__(self) -> str:
        """Developer-friendly representation.
        
        Returns:
            str: BMR with value
        """
        return f"BMR(value={self.value})"
