"""UserData value object - user biometric and activity data."""

from dataclasses import dataclass
from typing import Literal

from .activity_level import ActivityLevel


@dataclass(frozen=True)
class UserData:
    """User biometric and activity data for profile calculation.
    
    Immutable value object containing all user data needed for
    BMR/TDEE calculations.
    
    Attributes:
        weight: Body weight in kilograms (30-300 kg)
        height: Height in centimeters (100-250 cm)
        age: Age in years (18-120)
        sex: Biological sex ('M' or 'F')
        activity_level: Physical activity level
    """
    
    weight: float
    height: float
    age: int
    sex: Literal['M', 'F']
    activity_level: ActivityLevel
    
    def __post_init__(self) -> None:
        """Validate user data constraints.
        
        Raises:
            ValueError: If any constraint is violated
        """
        # Import here to avoid circular dependency
        from ..exceptions.domain_errors import InvalidUserDataError
        
        if not (30.0 <= self.weight <= 300.0):
            raise InvalidUserDataError(
                f"Weight must be 30-300 kg, got {self.weight}"
            )
        
        if not (100.0 <= self.height <= 250.0):
            raise InvalidUserDataError(
                f"Height must be 100-250 cm, got {self.height}"
            )
        
        if not (18 <= self.age <= 120):
            raise InvalidUserDataError(
                f"Age must be 18-120 years, got {self.age}"
            )
        
        if self.sex not in ('M', 'F'):
            raise InvalidUserDataError(
                f"Sex must be 'M' or 'F', got {self.sex}"
            )
    
    def bmi(self) -> float:
        """Calculate Body Mass Index.
        
        Returns:
            float: BMI = weight (kg) / (height (m))^2
            
        Example:
            >>> data = UserData(weight=80.0, height=180.0, ...)
            >>> data.bmi()
            24.69
        """
        height_m = self.height / 100.0
        return self.weight / (height_m ** 2)
    
    def bmi_category(self) -> str:
        """Get BMI category classification.
        
        Returns:
            str: BMI category (underweight, normal, overweight, obese)
        """
        bmi_value = self.bmi()
        if bmi_value < 18.5:
            return "underweight"
        elif bmi_value < 25.0:
            return "normal"
        elif bmi_value < 30.0:
            return "overweight"
        else:
            return "obese"
