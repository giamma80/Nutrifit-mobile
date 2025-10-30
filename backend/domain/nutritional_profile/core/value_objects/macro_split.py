"""MacroSplit value object - macronutrient distribution."""

from dataclasses import dataclass


@dataclass(frozen=True)
class MacroSplit:
    """Macronutrient distribution in grams.
    
    Represents daily target for protein, carbohydrates, and fat.
    Uses standard calorie conversion: protein 4 kcal/g, carbs 4 kcal/g,
    fat 9 kcal/g.
    
    Attributes:
        protein_g: Protein in grams (must be positive)
        carbs_g: Carbohydrates in grams (must be positive)
        fat_g: Fat in grams (must be positive)
    """
    
    protein_g: int
    carbs_g: int
    fat_g: int
    
    def __post_init__(self) -> None:
        """Validate macronutrients are positive.
        
        Raises:
            ValueError: If any macronutrient is not positive
        """
        if self.protein_g < 0:
            raise ValueError(
                f"Protein must be non-negative, got {self.protein_g}"
            )
        if self.carbs_g < 0:
            raise ValueError(
                f"Carbs must be non-negative, got {self.carbs_g}"
            )
        if self.fat_g < 0:
            raise ValueError(
                f"Fat must be non-negative, got {self.fat_g}"
            )
    
    def total_calories(self) -> float:
        """Calculate total calories from macronutrients.
        
        Returns:
            float: Total calories (protein×4 + carbs×4 + fat×9)
            
        Example:
            >>> split = MacroSplit(protein_g=176, carbs_g=248, fat_g=63)
            >>> split.total_calories()
            2259.0
        """
        return (self.protein_g * 4) + (self.carbs_g * 4) + (self.fat_g * 9)
    
    def protein_percentage(self) -> float:
        """Calculate protein percentage of total calories.
        
        Returns:
            float: Protein percentage (0-100)
        """
        total = self.total_calories()
        if total == 0:
            return 0.0
        return (self.protein_g * 4) / total * 100
    
    def carbs_percentage(self) -> float:
        """Calculate carbs percentage of total calories.
        
        Returns:
            float: Carbs percentage (0-100)
        """
        total = self.total_calories()
        if total == 0:
            return 0.0
        return (self.carbs_g * 4) / total * 100
    
    def fat_percentage(self) -> float:
        """Calculate fat percentage of total calories.
        
        Returns:
            float: Fat percentage (0-100)
        """
        total = self.total_calories()
        if total == 0:
            return 0.0
        return (self.fat_g * 9) / total * 100
    
    def __str__(self) -> str:
        """String representation.
        
        Returns:
            str: Macros in P/C/F format
        """
        return f"{self.protein_g}P / {self.carbs_g}C / {self.fat_g}F"
    
    def __repr__(self) -> str:
        """Developer-friendly representation.
        
        Returns:
            str: MacroSplit with grams
        """
        return (
            f"MacroSplit(protein_g={self.protein_g}, "
            f"carbs_g={self.carbs_g}, fat_g={self.fat_g})"
        )
