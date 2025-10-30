"""Goal value object - user's nutritional objective."""

from enum import Enum


class Goal(str, Enum):
    """User's nutritional goal determining calorie adjustment.
    
    - CUT: Weight loss with calorie deficit (~-500 kcal/day)
    - MAINTAIN: Weight maintenance at TDEE
    - BULK: Muscle gain with calorie surplus (~+300 kcal/day)
    """
    
    CUT = "cut"
    MAINTAIN = "maintain"
    BULK = "bulk"
    
    def calorie_adjustment(self, tdee: float) -> float:
        """Apply calorie adjustment to TDEE based on goal.
        
        Args:
            tdee: Total Daily Energy Expenditure (kcal/day)
            
        Returns:
            float: Adjusted calories target
            
        Example:
            >>> goal = Goal.CUT
            >>> goal.calorie_adjustment(2500.0)
            2000.0
        """
        adjustments = {
            Goal.CUT: -500,
            Goal.MAINTAIN: 0,
            Goal.BULK: +300
        }
        return tdee + adjustments[self]
    
    def protein_multiplier(self) -> float:
        """Get protein requirement multiplier (g/kg body weight).
        
        Returns:
            float: Protein grams per kg body weight
            
        Example:
            >>> Goal.CUT.protein_multiplier()
            2.2
        """
        multipliers = {
            Goal.CUT: 2.2,      # Higher protein to preserve muscle
            Goal.MAINTAIN: 1.8,  # Standard protein intake
            Goal.BULK: 2.0       # Moderate protein for muscle growth
        }
        return multipliers[self]
    
    def fat_percentage(self) -> float:
        """Get fat calories percentage of total.
        
        Returns:
            float: Fat percentage (0.0-1.0)
            
        Example:
            >>> Goal.CUT.fat_percentage()
            0.25
        """
        percentages = {
            Goal.CUT: 0.25,      # 25% fat
            Goal.MAINTAIN: 0.30,  # 30% fat
            Goal.BULK: 0.20       # 20% fat (more room for carbs)
        }
        return percentages[self]
