"""Infrastructure adapters for ML services.

These adapters bridge the domain ML services with the infrastructure layer,
providing dependency injection and configuration management.
"""

from domain.nutritional_profile.ml.kalman_tdee import KalmanTDEEService
from domain.nutritional_profile.ml.weight_forecast import (
    WeightForecastService,
    WeightForecast,
)
from domain.nutritional_profile.core.ports import (
    IAdaptiveTDEEService,
    IWeightForecastService,
)
from domain.nutritional_profile.core.entities import ProgressRecord
from typing import List, Tuple
from datetime import date


class KalmanTDEEAdapter(IAdaptiveTDEEService):
    """Adapter for Kalman filter-based adaptive TDEE tracking.

    This adapter implements the IAdaptiveTDEEService port, bridging
    the domain service interface with the ML implementation.

    It manages the Kalman filter lifecycle and provides a clean
    interface for updating TDEE estimates based on progress data.
    """

    def __init__(
        self,
        initial_tdee: float,
        initial_variance: float = 10000.0,
        process_noise: float = 50.0,
        measurement_noise: float = 0.01,
    ) -> None:
        """Initialize Kalman TDEE adapter.

        Args:
            initial_tdee: Initial TDEE estimate (kcal/day)
            initial_variance: Initial uncertainty (variance)
            process_noise: Daily TDEE variance
            measurement_noise: Weight measurement variance
        """
        self._service = KalmanTDEEService(
            initial_tdee=initial_tdee,
            initial_variance=initial_variance,
            process_noise=process_noise,
            measurement_noise=measurement_noise,
        )

    def update_with_progress(
        self,
        progress: ProgressRecord,
    ) -> float:
        """Update TDEE estimate with new progress data.

        Args:
            progress: Progress record with weight and calorie data

        Returns:
            Updated TDEE estimate (kcal/day)
        """
        consumed = progress.consumed_calories or 0.0
        return self._service.update(
            weight_kg=progress.weight,
            consumed_calories=consumed,
        )

    def update_batch(
        self,
        progress_records: List[ProgressRecord],
    ) -> float:
        """Update TDEE with multiple progress records.

        Processes records in order, updating the filter state
        sequentially.

        Args:
            progress_records: List of progress records (sorted by date)

        Returns:
            Final TDEE estimate after all updates (kcal/day)
        """
        tdee = self._service.state.tdee
        for record in progress_records:
            tdee = self.update_with_progress(record)
        return tdee

    def get_current_estimate(self) -> Tuple[float, float]:
        """Get current TDEE estimate with uncertainty.

        Returns:
            Tuple of (tdee_estimate, standard_deviation) in kcal/day
        """
        return self._service.get_estimate()

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
        return self._service.get_confidence_interval(confidence_level)

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
        self._service.reset(new_tdee, new_variance)


class WeightForecastAdapter(IWeightForecastService):
    """Adapter for weight forecasting service.

    This adapter implements the IWeightForecastService port, providing
    a clean interface for generating weight predictions based on
    historical progress data.
    """

    def __init__(self) -> None:
        """Initialize weight forecast adapter."""
        self._service = WeightForecastService()

    def forecast_from_progress(
        self,
        progress_records: List[ProgressRecord],
        days_ahead: int = 30,
        confidence_level: float = 0.95,
    ) -> WeightForecast:
        """Generate weight forecast from progress records.

        Args:
            progress_records: Historical progress data (sorted by date)
            days_ahead: Number of days to forecast
            confidence_level: Confidence level for intervals (0.0-1.0)

        Returns:
            WeightForecast with predictions and confidence bounds

        Raises:
            ValueError: If insufficient or invalid data
        """
        # Extract dates and weights from progress records
        dates = [record.date for record in progress_records]
        weights = [record.weight for record in progress_records]

        return self._service.forecast(
            dates=dates,
            weights=weights,
            days_ahead=days_ahead,
            confidence_level=confidence_level,
        )

    def forecast_from_data(
        self,
        dates: List[date],
        weights: List[float],
        days_ahead: int = 30,
        confidence_level: float = 0.95,
    ) -> WeightForecast:
        """Generate weight forecast from raw data.

        Args:
            dates: Historical dates (sorted, ascending)
            weights: Historical weights in kg
            days_ahead: Number of days to forecast
            confidence_level: Confidence level for intervals (0.0-1.0)

        Returns:
            WeightForecast with predictions and confidence bounds
        """
        return self._service.forecast(
            dates=dates,
            weights=weights,
            days_ahead=days_ahead,
            confidence_level=confidence_level,
        )
