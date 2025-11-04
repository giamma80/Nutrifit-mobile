"""Adapter for BMR calculation service."""

from domain.nutritional_profile.calculation.bmr_service import BMRService
from domain.nutritional_profile.core.ports.calculators import IBMRCalculator
from domain.nutritional_profile.core.value_objects.bmr import BMR
from domain.nutritional_profile.core.value_objects.user_data import UserData


class BMRCalculatorAdapter(IBMRCalculator):
    """
    Adapter for BMR calculation service.

    Wraps the domain calculation service to implement the port interface.
    """

    def __init__(self) -> None:
        """Initialize adapter with BMR service."""
        self._service = BMRService()

    def calculate(self, user_data: UserData) -> BMR:
        """
        Calculate BMR using Mifflin-St Jeor formula.

        Args:
            user_data: User biometric data

        Returns:
            BMR value object

        Raises:
            ValueError: If user data is invalid
        """
        return self._service.calculate(user_data)
