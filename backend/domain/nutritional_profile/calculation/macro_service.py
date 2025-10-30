"""MacroService - Macronutrient distribution calculation."""

from ..core.ports.calculators import IMacroCalculator
from ..core.value_objects.goal import Goal
from ..core.value_objects.macro_split import MacroSplit


class MacroService(IMacroCalculator):
    """Calculate macronutrient distribution based on goal.
    
    Distributes daily calories into protein, carbohydrates, and fat
    using goal-specific strategies:
    
    Cut (weight loss):
        - Protein: 2.2g/kg (preserve muscle in deficit)
        - Fat: 25% of calories
        - Carbs: Remaining calories
        
    Maintain (maintenance):
        - Protein: 1.8g/kg (adequate protein)
        - Fat: 30% of calories
        - Carbs: Remaining calories
        
    Bulk (muscle gain):
        - Protein: 2.0g/kg (support muscle growth)
        - Fat: 20% of calories (more room for carbs)
        - Carbs: Remaining calories (fuel training)
    
    Calorie conversion:
        - Protein: 4 kcal/g
        - Carbohydrates: 4 kcal/g
        - Fat: 9 kcal/g
    """
    
    def calculate(
        self,
        calories_target: float,
        weight: float,
        goal: Goal
    ) -> MacroSplit:
        """Calculate macro distribution.
        
        Args:
            calories_target: Daily calorie target
            weight: Body weight in kg
            goal: Nutritional goal
            
        Returns:
            MacroSplit: Protein/carbs/fat in grams
            
        Example:
            >>> service = MacroService()
            >>> split = service.calculate(
            ...     calories_target=2259.0,
            ...     weight=80.0,
            ...     goal=Goal.CUT
            ... )
            >>> split.protein_g
            176  # 80kg × 2.2
            >>> split.fat_g
            63   # 2259 × 0.25 / 9
            >>> split.carbs_g
            248  # (2259 - 704 - 565) / 4
        """
        # 1. Calculate protein (goal-dependent g/kg)
        protein_multiplier = goal.protein_multiplier()
        protein_g = round(weight * protein_multiplier)
        protein_cal = protein_g * 4
        
        # 2. Calculate fat (goal-dependent percentage)
        fat_percentage = goal.fat_percentage()
        fat_cal = calories_target * fat_percentage
        fat_g = round(fat_cal / 9)
        
        # 3. Calculate carbs (remaining calories)
        carb_cal = calories_target - (protein_cal + fat_cal)
        carbs_g = round(carb_cal / 4)
        
        # Ensure non-negative values (edge case for very low calories)
        carbs_g = max(0, carbs_g)
        
        return MacroSplit(
            protein_g=protein_g,
            carbs_g=carbs_g,
            fat_g=fat_g
        )
