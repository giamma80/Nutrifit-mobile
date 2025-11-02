"""Adapter for TDEE calculation service."""

from domain.nutritional_profile.calculation.tdee_service import TDEEService
from domain.nutritional_profile.core.ports.calculators import (
    ITDEECalculator,
)
from domain.nutritional_profile.core.value_objects.activity_level import (
    ActivityLevel,
)
from domain.nutritional_profile.core.value_objects.bmr import BMR
from domain.nutritional_profile.core.value_objects.tdee import TDEE


class TDEECalculatorAdapter(ITDEECalculator):
    """
    Adapter for TDEE calculation service.

    Wraps the domain calculation service to implement the port interface.
    """

    def __init__(self) -> None:
        """Initialize adapter with TDEE service."""
        self._service = TDEEService()

    def calculate(self, bmr: BMR, activity_level: ActivityLevel) -> TDEE:
        """
        Calculate TDEE by multiplying BMR with activity factor.

        Args:
            bmr: Basal metabolic rate
            activity_level: Physical activity level

        Returns:
            TDEE value object

        Raises:
            ValueError: If inputs are invalid
        """
        return self._service.calculate(bmr, activity_level)
