"""ML service ports for nutritional profile domain.

These interfaces define the contracts for ML-enhanced services
that can be provided by the infrastructure layer.
"""

from abc import ABC, abstractmethod
from typing import List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from domain.nutritional_profile.core.entities import ProgressRecord
    from domain.nutritional_profile.ml.weight_forecast import WeightForecast
    from datetime import date


class IAdaptiveTDEEService(ABC):
    """Port for adaptive TDEE tracking service.

    This service uses machine learning (Kalman filtering) to adaptively
    estimate a user's true TDEE based on observed weight changes and
    calorie intake over time.
    """

    @abstractmethod
    def update_with_progress(
        self,
        progress: "ProgressRecord",
    ) -> float:
        """Update TDEE estimate with new progress data.

        Args:
            progress: Progress record with weight and calorie data

        Returns:
            Updated TDEE estimate (kcal/day)
        """
        pass

    @abstractmethod
    def update_batch(
        self,
        progress_records: List["ProgressRecord"],
    ) -> float:
        """Update TDEE with multiple progress records.

        Args:
            progress_records: List of progress records (sorted by date)

        Returns:
            Final TDEE estimate after all updates (kcal/day)
        """
        pass

    @abstractmethod
    def get_current_estimate(self) -> Tuple[float, float]:
        """Get current TDEE estimate with uncertainty.

        Returns:
            Tuple of (tdee_estimate, standard_deviation) in kcal/day
        """
        pass

    @abstractmethod
    def get_confidence_interval(
        self,
        confidence_level: float = 0.95,
    ) -> Tuple[float, float]:
        """Get confidence interval for current TDEE estimate.

        Args:
            confidence_level: Confidence level (0.0-1.0)

        Returns:
            Tuple of (lower_bound, upper_bound) in kcal/day
        """
        pass

    @abstractmethod
    def reset(
        self,
        new_tdee: float,
        new_variance: float = 10000.0,
    ) -> None:
        """Reset filter to new initial values.

        Args:
            new_tdee: New TDEE estimate (kcal/day)
            new_variance: New initial uncertainty (variance)
        """
        pass


class IWeightForecastService(ABC):
    """Port for weight forecasting service.

    This service uses time series analysis to predict future weight
    trajectory based on historical data, providing point estimates
    and confidence intervals.
    """

    @abstractmethod
    def forecast_from_progress(
        self,
        progress_records: List["ProgressRecord"],
        days_ahead: int = 30,
        confidence_level: float = 0.95,
    ) -> "WeightForecast":
        """Generate weight forecast from progress records.

        Args:
            progress_records: Historical progress data (sorted by date)
            days_ahead: Number of days to forecast
            confidence_level: Confidence level for intervals (0.0-1.0)

        Returns:
            WeightForecast with predictions and confidence bounds
        """
        pass

    @abstractmethod
    def forecast_from_data(
        self,
        dates: List["date"],
        weights: List[float],
        days_ahead: int = 30,
        confidence_level: float = 0.95,
    ) -> "WeightForecast":
        """Generate weight forecast from raw data.

        Args:
            dates: Historical dates (sorted, ascending)
            weights: Historical weights in kg
            days_ahead: Number of days to forecast
            confidence_level: Confidence level for intervals (0.0-1.0)

        Returns:
            WeightForecast with predictions and confidence bounds
        """
        pass
