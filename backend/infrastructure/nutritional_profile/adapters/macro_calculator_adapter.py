"""Adapter for Macro calculation service."""

from domain.nutritional_profile.calculation.macro_service import MacroService
from domain.nutritional_profile.core.ports.calculators import (
    IMacroCalculator,
)
from domain.nutritional_profile.core.value_objects.goal import Goal
from domain.nutritional_profile.core.value_objects.macro_split import (
    MacroSplit,
)


class MacroCalculatorAdapter(IMacroCalculator):
    """
    Adapter for Macro calculation service.

    Wraps the domain calculation service to implement the port interface.
    """

    def __init__(self) -> None:
        """Initialize adapter with Macro service."""
        self._service = MacroService()

    def calculate(self, calories_target: float, weight: float, goal: Goal) -> MacroSplit:
        """
        Calculate macronutrient distribution based on goal.

        Args:
            calories_target: Daily calorie target
            weight: Body weight in kg
            goal: Nutritional goal (cut/maintain/bulk)

        Returns:
            MacroSplit value object

        Raises:
            ValueError: If inputs are invalid
        """
        return self._service.calculate(calories_target, weight, goal)
