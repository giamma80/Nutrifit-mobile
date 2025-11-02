"""BMRService - Basal Metabolic Rate calculation."""

from ..core.ports.calculators import IBMRCalculator
from ..core.value_objects.bmr import BMR
from ..core.value_objects.user_data import UserData


class BMRService(IBMRCalculator):
    """Calculate Basal Metabolic Rate using Mifflin-St Jeor equation.

    The Mifflin-St Jeor equation is considered the most accurate formula
    for BMR calculation in normal-weight and overweight individuals.

    Formula:
        Men:   BMR = 10 × weight(kg) + 6.25 × height(cm) - 5 × age + 5
        Women: BMR = 10 × weight(kg) + 6.25 × height(cm) - 5 × age - 161

    References:
        Mifflin MD, St Jeor ST, Hill LA, et al. A new predictive equation
        for resting energy expenditure in healthy individuals.
        Am J Clin Nutr. 1990;51(2):241-247.
    """

    def calculate(self, user_data: UserData) -> BMR:
        """Calculate BMR from user biometric data.

        Args:
            user_data: User biometric data (weight, height, age, sex)

        Returns:
            BMR: Calculated basal metabolic rate in kcal/day

        Example:
            >>> service = BMRService()
            >>> data = UserData(
            ...     weight=80.0,
            ...     height=180.0,
            ...     age=30,
            ...     sex='M',
            ...     activity_level=ActivityLevel.MODERATE
            ... )
            >>> bmr = service.calculate(data)
            >>> bmr.value
            1780.0
        """
        # Base calculation (common for both sexes)
        base = 10 * user_data.weight + 6.25 * user_data.height - 5 * user_data.age

        # Sex-specific adjustment
        if user_data.sex == "M":
            bmr_value = base + 5
        else:  # 'F'
            bmr_value = base - 161

        return BMR(value=bmr_value)
